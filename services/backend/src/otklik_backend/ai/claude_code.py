import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any, AsyncIterator

import litellm
from litellm import CustomLLM, ModelResponse  # type: ignore[attr-defined]
from litellm.types.utils import GenericStreamingChunk
from litellm.utils import custom_llm_setup

from otklik_backend.log import get_logger
from otklik_backend.paths import AppPaths
from otklik_backend.setup.constants import CLAUDE_CODE_PREFIX, CLAUDE_CODE_PROVIDER

log = get_logger(__name__)

DEFAULT_TIMEOUT_SEC = 180.0

STREAM_IDLE_TIMEOUT_SEC = 120.0


class ClaudeCodeError(Exception): ...


_PROXY: str | None = None


def set_claude_proxy(proxy_url: str | None) -> None:
    global _PROXY
    _PROXY = (proxy_url or "").strip() or None


def _error_detail(stdout: bytes, stderr: bytes) -> str:
    err = stderr.decode(errors="replace").strip()
    out = stdout.decode(errors="replace").strip()
    if out:
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            status = data.get("api_error_status")
            result = str(data.get("result") or data.get("error") or "").strip()
            combined = f"HTTP {status}: {result}" if status else result
            if combined:
                return combined[-500:]
    return (err or out or "нет вывода от claude")[-500:]


def resolve_claude_binary() -> str | None:
    found = shutil.which("claude")
    if found:
        return found
    for candidate in (
        Path.home() / ".local" / "bin" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/opt/homebrew/bin/claude"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def _clean_cwd() -> str:
    root = AppPaths().root
    root.mkdir(parents=True, exist_ok=True)
    return str(root)


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    if _PROXY:
        for var in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
            env[var] = _PROXY
    return env


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        return "\n".join(parts)
    return ""


def _messages_to_prompt(messages: list[dict[str, Any]]) -> tuple[str, str]:
    system_parts: list[str] = []
    convo_parts: list[str] = []
    for msg in messages:
        role = msg.get("role")
        text = _text_of(msg.get("content"))
        if role == "system":
            system_parts.append(text)
        elif role == "assistant":
            convo_parts.append(f"Assistant: {text}")
        else:
            convo_parts.append(f"User: {text}")
    return "\n\n".join(system_parts), "\n\n".join(convo_parts)


def _strip_prefix(model: str) -> str:
    if model.startswith(CLAUDE_CODE_PREFIX):
        return model[len(CLAUDE_CODE_PREFIX) :]
    return model


class ClaudeCodeLLM(CustomLLM):
    def _base_args(
        self, binary: str, model: str, system: str, prompt: str
    ) -> list[str]:
        return [
            binary,
            "-p",
            prompt,
            "--append-system-prompt",
            system,
            "--model",
            _strip_prefix(model),
            "--permission-mode",
            "dontAsk",
        ]

    async def _spawn(self, args: list[str]) -> asyncio.subprocess.Process:
        return await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=_clean_cwd(),
            env=_clean_env(),
        )

    async def acompletion(self, *args: Any, **kwargs: Any) -> ModelResponse:
        model: str = kwargs["model"]
        messages: list[dict[str, Any]] = kwargs["messages"]
        timeout: float = kwargs.get("timeout") or DEFAULT_TIMEOUT_SEC
        binary = resolve_claude_binary()
        if binary is None:
            log.warning("claude-code: binary not found")
            raise ClaudeCodeError("Claude Code CLI (`claude`) not found")
        system, prompt = _messages_to_prompt(messages)
        proc_args = self._base_args(binary, model, system, prompt) + [
            "--output-format",
            "json",
        ]
        try:
            proc = await self._spawn(proc_args)
        except OSError as exc:
            log.warning("claude-code: failed to spawn %s: %s", binary, exc)
            raise ClaudeCodeError(
                f"failed to spawn `claude` binary at {binary!r}: {exc}"
            ) from exc
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
        except (asyncio.TimeoutError, TimeoutError) as exc:
            proc.kill()
            await proc.wait()
            log.warning("claude-code: `claude -p` timed out after %.0fs", timeout)
            raise ClaudeCodeError(
                f"`claude -p` timed out after {timeout:.0f}s"
            ) from exc
        if proc.returncode != 0:
            detail = _error_detail(stdout, stderr)
            log.warning(
                "claude-code: `claude -p` exited %s: %s", proc.returncode, detail
            )
            raise ClaudeCodeError(f"`claude -p` exited {proc.returncode}: {detail}")
        try:
            data = json.loads(stdout.decode(errors="replace"))
        except json.JSONDecodeError as exc:
            log.warning("claude-code: `claude -p` returned non-JSON output: %s", exc)
            raise ClaudeCodeError(
                f"`claude -p` returned non-JSON output: {exc}"
            ) from exc
        if data.get("is_error"):
            log.warning(
                "claude-code: `claude -p` reported an error: %s",
                str(data.get("result", ""))[:300],
            )
            raise ClaudeCodeError(
                f"`claude -p` reported an error: {str(data.get('result', ''))[:300]}"
            )
        return self._to_response(model, data)

    async def astreaming(  # type: ignore[override]
        self, *args: Any, **kwargs: Any
    ) -> AsyncIterator[GenericStreamingChunk]:
        model: str = kwargs["model"]
        messages: list[dict[str, Any]] = kwargs["messages"]
        binary = resolve_claude_binary()
        if binary is None:
            raise ClaudeCodeError("Claude Code CLI (`claude`) not found")
        system, prompt = _messages_to_prompt(messages)
        proc_args = self._base_args(binary, model, system, prompt) + [
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-partial-messages",
        ]
        try:
            proc = await self._spawn(proc_args)
        except OSError as exc:
            log.warning("claude-code: failed to spawn %s: %s", binary, exc)
            raise ClaudeCodeError(
                f"failed to spawn `claude` binary at {binary!r}: {exc}"
            ) from exc
        assert proc.stdout is not None
        stderr_task: asyncio.Task[bytes] | None = None
        if proc.stderr is not None:
            stderr_task = asyncio.create_task(proc.stderr.read())
        final_usage: dict[str, int] | None = None
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(
                        proc.stdout.readline(), STREAM_IDLE_TIMEOUT_SEC
                    )
                except (asyncio.TimeoutError, TimeoutError) as exc:
                    log.warning(
                        "claude-code: `claude -p` (stream) idle for over %.0fs, "
                        "killing",
                        STREAM_IDLE_TIMEOUT_SEC,
                    )
                    raise ClaudeCodeError(
                        "`claude -p` (stream) stream idle timed out after "
                        f"{STREAM_IDLE_TIMEOUT_SEC:.0f}s"
                    ) from exc
                if not raw:
                    break
                line = raw.decode(errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                etype = event.get("type")
                if etype == "stream_event":
                    inner = event.get("event", {})
                    if inner.get("type") == "content_block_delta":
                        delta = inner.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield {
                                "text": str(delta.get("text", "")),
                                "is_finished": False,
                                "finish_reason": "",
                                "usage": None,
                                "index": 0,
                            }
                elif etype == "result":
                    u = event.get("usage") or {}
                    in_tok = int(u.get("input_tokens", 0) or 0)
                    out_tok = int(u.get("output_tokens", 0) or 0)
                    final_usage = {
                        "prompt_tokens": in_tok,
                        "completion_tokens": out_tok,
                        "total_tokens": in_tok + out_tok,
                    }
            await proc.wait()
            stderr_tail = ""
            if stderr_task is not None:
                stderr_tail = (await stderr_task).decode(errors="replace")[-500:]
            if proc.returncode not in (0, None):
                log.warning(
                    "claude-code: `claude -p` (stream) exited %s: %s",
                    proc.returncode,
                    stderr_tail,
                )
                raise ClaudeCodeError(
                    f"`claude -p` (stream) exited {proc.returncode}: {stderr_tail}"
                )
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            if stderr_task is not None and not stderr_task.done():
                stderr_task.cancel()
                try:
                    await stderr_task
                except asyncio.CancelledError:
                    pass
        yield {
            "text": "",
            "is_finished": True,
            "finish_reason": "stop",
            "usage": final_usage,  # type: ignore[typeddict-item]
            "index": 0,
        }

    @staticmethod
    def _to_response(model: str, data: dict[str, Any]) -> ModelResponse:
        usage = data.get("usage") or {}
        in_tok = int(usage.get("input_tokens", 0) or 0)
        out_tok = int(usage.get("output_tokens", 0) or 0)
        response = ModelResponse(
            id=str(data.get("session_id", "claude-code")),
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": str(data.get("result", "")),
                    },
                    "finish_reason": "stop",
                }
            ],
            model=str(data.get("model", model)),
            usage={
                "prompt_tokens": in_tok,
                "completion_tokens": out_tok,
                "total_tokens": in_tok + out_tok,
            },
        )
        response._hidden_params["response_cost"] = float(
            data.get("total_cost_usd", 0.0) or 0.0
        )
        return response


def register_claude_code_provider() -> None:
    for item in litellm.custom_provider_map:
        if item.get("provider") == CLAUDE_CODE_PROVIDER:
            return
    litellm.custom_provider_map = [
        *litellm.custom_provider_map,
        {"provider": CLAUDE_CODE_PROVIDER, "custom_handler": ClaudeCodeLLM()},
    ]
    custom_llm_setup()  # type: ignore[no-untyped-call]
