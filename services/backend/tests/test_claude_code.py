import json
from unittest.mock import patch

import litellm
import pytest
from litellm import ModelResponse

from otklik_backend.ai.claude_code import (
    ClaudeCodeError,
    ClaudeCodeLLM,
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
