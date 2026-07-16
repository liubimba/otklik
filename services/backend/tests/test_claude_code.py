import asyncio
import json
from unittest.mock import patch

import litellm
import pytest
from litellm import ModelResponse

from otklik_backend.ai.claude_code import (
    ClaudeCodeError,
    ClaudeCodeLLM,
    _clean_env,
    _messages_to_prompt,
    register_claude_code_provider,
    resolve_claude_binary,
)


class _FakeProc:
    """Подделка asyncio subprocess: отдаёт заранее заданный stdout/stderr/код."""

    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
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
    proc = _FakeProc()

    async def _fake_wait_for(coro, timeout):
        coro.close()  # avoid "coroutine was never awaited" warning
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
    """Подделка asyncio.StreamReader: одноразовый async `read()`."""

    def __init__(self, data: bytes = b""):
        self._data = data

    async def read(self, _n: int = -1) -> bytes:
        return self._data


class _FakeStdout:
    """Подделка asyncio.StreamReader: `readline()` по списку, затем EOF (b"")."""

    def __init__(self, lines: list[bytes]):
        self._lines = list(lines)

    async def readline(self) -> bytes:
        if not self._lines:
            return b""
        return self._lines.pop(0)


class _FakeStreamProc:
    """Подделка процесса со stdout-строками stream-json."""

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
    # промежуточные дельты не финальные
    assert all(c["is_finished"] is False for c in chunks[:-1])


async def test_astreaming_raises_on_mid_stream_death_without_result() -> None:
    """`claude -p` умирает/обрывается до строки "result" — стрим должен
    поднять ClaudeCodeError, а не молча выдать терминальный чанк успеха
    (иначе letter-edit chat подсунет пользователю обрезанное письмо)."""
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
    """`claude -p` (stream) перестаёт писать в stdout, но не завершается —
    цикл чтения должен оборваться по дедлайну бездействия между чанками, а
    не повиснуть навечно (иначе letter-edit chat зависает без ответа)."""
    llm = ClaudeCodeLLM()
    proc = _FakeStreamProc([], returncode=None)  # ещё "жив" — не вышел

    async def _fake_exec(*args, **kwargs):
        return proc

    async def _fake_wait_for(coro, timeout):
        coro.close()  # avoid "coroutine was never awaited" warning
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
    assert proc.returncode == -9  # killed & reaped in `finally`


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
