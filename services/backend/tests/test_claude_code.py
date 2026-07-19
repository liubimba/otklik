import asyncio
import json
import os
import signal
import tempfile
import textwrap
import time
from unittest.mock import patch

import litellm
import pytest
from litellm import ModelResponse

from otklik_backend.ai.claude_code import (
    ClaudeCodeError,
    ClaudeCodeLLM,
    _clean_env,
    _error_detail,
    _messages_to_prompt,
    register_claude_code_provider,
    resolve_claude_binary,
    set_claude_proxy,
)


class _FakeProc:
    def __init__(
        self, stdout: bytes = b"", stderr: bytes = b"", returncode: int | None = 0
    ):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode

    async def communicate(self, _input: bytes | None = None) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode


def _spawn_returns(proc: _FakeProc):
    async def _fake_exec(*args, **kwargs):
        return proc

    return patch(
        "otklik_backend.ai.claude_code.asyncio.create_subprocess_exec",
        side_effect=_fake_exec,
    )


def _json_output(
    result: str, in_tok: int = 3, out_tok: int = 7, cost: float = 0.01
) -> bytes:
    return json.dumps(
        {
            "result": result,
            "session_id": "s1",
            "model": "claude-sonnet",
            "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
            "total_cost_usd": cost,
        }
    ).encode()


def test_messages_to_prompt_splits_system_and_flattens_turns() -> None:
    messages = [
        {"role": "system", "content": "SYS-A"},
        {"role": "system", "content": "SYS-B"},
        {"role": "user", "content": [{"type": "text", "text": "hello"}]},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": [{"type": "text", "text": "make it shorter"}]},
    ]
    system, prompt = _messages_to_prompt(messages)
    assert system == "SYS-A\n\nSYS-B"
    assert "User: hello" in prompt
    assert "Assistant: hi there" in prompt
    assert "User: make it shorter" in prompt


async def test_acompletion_parses_result_and_usage() -> None:
    llm = ClaudeCodeLLM()
    proc = _FakeProc(stdout=_json_output("Здравствуйте! Готов обсудить.", 5, 11, 0.02))
    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        _spawn_returns(proc),
    ):
        response = await llm.acompletion(
            model="claude-code/sonnet",
            messages=[{"role": "user", "content": [{"type": "text", "text": "go"}]}],
            model_response=ModelResponse(),
        )
    assert response.choices[0].message.content == "Здравствуйте! Готов обсудить."
    assert response.usage.prompt_tokens == 5
    assert response.usage.completion_tokens == 11
    assert response._hidden_params["response_cost"] == 0.02


async def test_acompletion_raises_when_binary_missing() -> None:
    llm = ClaudeCodeLLM()
    with patch(
        "otklik_backend.ai.claude_code.resolve_claude_binary", return_value=None
    ):
        with pytest.raises(ClaudeCodeError, match="not found"):
            await llm.acompletion(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            )


async def test_acompletion_raises_on_nonzero_exit() -> None:
    llm = ClaudeCodeLLM()
    proc = _FakeProc(stdout=b"", stderr=b"not logged in", returncode=1)
    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        _spawn_returns(proc),
    ):
        with pytest.raises(ClaudeCodeError, match="exited 1"):
            await llm.acompletion(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            )


async def test_acompletion_surfaces_stdout_error_when_stderr_empty() -> None:
    llm = ClaudeCodeLLM()
    proc = _FakeProc(
        stdout=json.dumps(
            {
                "is_error": True,
                "api_error_status": 403,
                "result": "API Error: Forbidden",
            }
        ).encode(),
        stderr=b"",
        returncode=1,
    )
    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        _spawn_returns(proc),
    ):
        with pytest.raises(ClaudeCodeError, match="403"):
            await llm.acompletion(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            )


def test_error_detail_prefers_structured_stdout_error() -> None:
    out = json.dumps({"result": "API Error: Forbidden"}).encode()
    assert _error_detail(out, b"Shell cwd was reset") == "API Error: Forbidden"


def test_error_detail_uses_stderr_when_stdout_has_no_structured_error() -> None:
    assert _error_detail(b"random noise", b"real crash") == "real crash"


def test_error_detail_extracts_stdout_json_when_stderr_empty() -> None:
    out = json.dumps({"api_error_status": 401, "result": "Unauthorized"}).encode()
    assert _error_detail(out, b"") == "HTTP 401: Unauthorized"


def test_error_detail_falls_back_when_no_output() -> None:
    assert _error_detail(b"", b"") == "нет вывода от claude"


def test_clean_env_injects_configured_proxy() -> None:
    set_claude_proxy("http://127.0.0.1:10809")
    try:
        env = _clean_env()
        assert env["HTTPS_PROXY"] == "http://127.0.0.1:10809"
        assert env["ALL_PROXY"] == "http://127.0.0.1:10809"
    finally:
        set_claude_proxy(None)
    assert _clean_env().get("HTTPS_PROXY") != "http://127.0.0.1:10809"


async def test_acompletion_raises_on_is_error_payload() -> None:
    llm = ClaudeCodeLLM()
    proc = _FakeProc(
        stdout=json.dumps({"result": "rate limited", "is_error": True}).encode()
    )
    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        _spawn_returns(proc),
    ):
        with pytest.raises(ClaudeCodeError, match="reported an error"):
            await llm.acompletion(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            )


async def test_acompletion_raises_on_non_json_stdout() -> None:
    llm = ClaudeCodeLLM()
    proc = _FakeProc(stdout=b"not json at all", returncode=0)
    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        _spawn_returns(proc),
    ):
        with pytest.raises(ClaudeCodeError, match="non-JSON"):
            await llm.acompletion(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            )


async def test_acompletion_raises_and_kills_process_on_timeout() -> None:
    llm = ClaudeCodeLLM()
    proc = _FakeProc(returncode=None)

    async def _fake_wait_for(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError

    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        _spawn_returns(proc),
        patch(
            "otklik_backend.ai.claude_code.asyncio.wait_for",
            side_effect=_fake_wait_for,
        ),
    ):
        with pytest.raises(ClaudeCodeError, match="timed out"):
            await llm.acompletion(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            )
    assert proc.returncode == -9


async def test_acompletion_raises_when_spawn_fails() -> None:
    llm = ClaudeCodeLLM()
    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        patch(
            "otklik_backend.ai.claude_code.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("no such file"),
        ),
    ):
        with pytest.raises(ClaudeCodeError, match="/usr/bin/claude"):
            await llm.acompletion(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            )


def test_register_is_idempotent() -> None:
    litellm.custom_provider_map = []
    register_claude_code_provider()
    register_claude_code_provider()
    claude = [m for m in litellm.custom_provider_map if m["provider"] == "claude-code"]
    assert len(claude) == 1


def test_resolve_binary_returns_none_without_install() -> None:
    with (
        patch("otklik_backend.ai.claude_code.shutil.which", return_value=None),
        patch("otklik_backend.ai.claude_code.Path.exists", return_value=False),
    ):
        assert resolve_claude_binary() is None


class _FakeAsyncReader:
    def __init__(self, data: bytes = b""):
        self._data = data

    async def read(self, _n: int = -1) -> bytes:
        return self._data


class _FakeStdout:
    def __init__(self, lines: list[bytes]):
        self._lines = list(lines)

    async def readline(self) -> bytes:
        if not self._lines:
            return b""
        return self._lines.pop(0)


class _FakeStreamProc:
    def __init__(
        self,
        lines: list[bytes],
        returncode: int | None = 0,
        stderr: bytes = b"",
    ):
        self.stdout = _FakeStdout(lines)
        self.stderr = _FakeAsyncReader(stderr)
        self.returncode = returncode

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode


def _stream_lines() -> list[bytes]:
    def delta(text: str) -> bytes:
        return (
            json.dumps(
                {
                    "type": "stream_event",
                    "event": {
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": text},
                    },
                }
            )
            + "\n"
        ).encode()

    result = (
        json.dumps(
            {
                "type": "result",
                "result": "Привет!",
                "usage": {"input_tokens": 4, "output_tokens": 2},
            }
        )
        + "\n"
    ).encode()
    return [delta("Прив"), delta("ет!"), result]


async def test_astreaming_yields_deltas_then_terminal_chunk() -> None:
    llm = ClaudeCodeLLM()
    proc = _FakeStreamProc(_stream_lines())

    async def _fake_exec(*args, **kwargs):
        return proc

    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        patch(
            "otklik_backend.ai.claude_code.asyncio.create_subprocess_exec",
            side_effect=_fake_exec,
        ),
    ):
        chunks = [
            chunk
            async for chunk in llm.astreaming(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            )
        ]

    texts = [c["text"] for c in chunks]
    assert "".join(texts) == "Прив" + "ет!"
    assert chunks[-1]["is_finished"] is True
    assert chunks[-1]["finish_reason"] == "stop"
    assert chunks[-1]["usage"]["completion_tokens"] == 2
    assert all(c["is_finished"] is False for c in chunks[:-1])


async def test_astreaming_raises_on_mid_stream_death_without_result() -> None:
    llm = ClaudeCodeLLM()
    delta_line = (
        json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "Прив"},
                },
            }
        )
        + "\n"
    ).encode()
    proc = _FakeStreamProc([delta_line], returncode=1, stderr=b"rate limited, aborting")

    async def _fake_exec(*args, **kwargs):
        return proc

    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        patch(
            "otklik_backend.ai.claude_code.asyncio.create_subprocess_exec",
            side_effect=_fake_exec,
        ),
    ):
        with pytest.raises(ClaudeCodeError, match="exited 1"):
            async for _ in llm.astreaming(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            ):
                pass


async def test_astreaming_raises_and_kills_process_on_idle_timeout() -> None:
    llm = ClaudeCodeLLM()
    proc = _FakeStreamProc([], returncode=None)

    async def _fake_exec(*args, **kwargs):
        return proc

    async def _fake_wait_for(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError

    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        patch(
            "otklik_backend.ai.claude_code.asyncio.create_subprocess_exec",
            side_effect=_fake_exec,
        ),
        patch(
            "otklik_backend.ai.claude_code.asyncio.wait_for",
            side_effect=_fake_wait_for,
        ),
    ):
        with pytest.raises(ClaudeCodeError, match="idle"):
            async for _ in llm.astreaming(
                model="claude-code/sonnet",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
            ):
                pass
    assert proc.returncode == -9


def test_resolve_timeout_caps_the_router_default_at_the_ceiling() -> None:
    from otklik_backend.ai.claude_code import DEFAULT_TIMEOUT_SEC, _resolve_timeout

    assert _resolve_timeout(6000.0) == DEFAULT_TIMEOUT_SEC
    assert _resolve_timeout(None) == DEFAULT_TIMEOUT_SEC
    assert _resolve_timeout(0) == DEFAULT_TIMEOUT_SEC
    assert _resolve_timeout(30) == 30.0


def _spawning_claude_script(pidfile: str) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
    handle.write(
        textwrap.dedent(
            f"""#!/bin/sh
            echo $$ >> "{pidfile}"
            sleep 300 &
            echo $! >> "{pidfile}"
            sleep 300
            """
        )
    )
    handle.close()
    os.chmod(handle.name, 0o755)
    return handle.name


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _reap(pids: list[int]) -> list[int]:
    survivors = [pid for pid in pids if _is_alive(pid)]
    for pid in survivors:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    return survivors


@pytest.mark.skipif(os.name != "posix", reason="process-group kill is posix-only")
async def test_acompletion_timeout_kills_whole_process_tree_without_stalling(
    tmp_path,
) -> None:
    pidfile = tmp_path / "pids"
    pidfile.write_text("")
    script = _spawning_claude_script(str(pidfile))
    llm = ClaudeCodeLLM()
    with patch(
        "otklik_backend.ai.claude_code.resolve_claude_binary", return_value=script
    ):
        start = time.monotonic()
        with pytest.raises(ClaudeCodeError, match="timed out"):
            await asyncio.wait_for(
                llm.acompletion(
                    model="claude-code/opus",
                    messages=[{"role": "user", "content": "go"}],
                    model_response=ModelResponse(),
                    timeout=1.0,
                ),
                timeout=20,
            )
        elapsed = time.monotonic() - start
    await asyncio.sleep(0.3)
    pids = [int(x) for x in pidfile.read_text().split()]
    survivors = _reap(pids)
    assert elapsed < 15
    assert survivors == []


@pytest.mark.skipif(os.name != "posix", reason="process-group kill is posix-only")
async def test_acompletion_cancellation_kills_the_process_tree(tmp_path) -> None:
    pidfile = tmp_path / "pids"
    pidfile.write_text("")
    script = _spawning_claude_script(str(pidfile))
    llm = ClaudeCodeLLM()
    with patch(
        "otklik_backend.ai.claude_code.resolve_claude_binary", return_value=script
    ):
        task = asyncio.create_task(
            llm.acompletion(
                model="claude-code/opus",
                messages=[{"role": "user", "content": "go"}],
                model_response=ModelResponse(),
                timeout=300,
            )
        )
        for _ in range(100):
            await asyncio.sleep(0.05)
            if len(pidfile.read_text().split()) >= 2:
                break
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    await asyncio.sleep(0.3)
    pids = [int(x) for x in pidfile.read_text().split()]
    survivors = _reap(pids)
    assert survivors == []


def test_clean_env_skips_socks_proxy_claude_cannot_use() -> None:
    set_claude_proxy("socks5://127.0.0.1:10808")
    try:
        env = _clean_env()
        assert "HTTPS_PROXY" not in env or not env["HTTPS_PROXY"].startswith("socks")
        assert "ALL_PROXY" not in env or not env["ALL_PROXY"].startswith("socks")
    finally:
        set_claude_proxy(None)


def test_clean_env_strips_api_key_and_auth_token() -> None:
    with patch(
        "otklik_backend.ai.claude_code.os.environ",
        {
            "ANTHROPIC_API_KEY": "sk-leaked",
            "ANTHROPIC_AUTH_TOKEN": "token-leaked",
            "ANTHROPIC_BASE_URL": "https://example.com",
            "PATH": "/usr/bin",
        },
    ):
        env = _clean_env()
    assert "ANTHROPIC_API_KEY" not in env
    assert "ANTHROPIC_AUTH_TOKEN" not in env
    assert env["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert env["PATH"] == "/usr/bin"
