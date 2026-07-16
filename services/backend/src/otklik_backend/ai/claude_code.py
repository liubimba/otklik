import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any

import litellm
from litellm import CustomLLM, ModelResponse  # type: ignore[attr-defined]

from otklik_backend.log import get_logger
from otklik_backend.paths import AppPaths
from otklik_backend.setup.constants import CLAUDE_CODE_PREFIX, CLAUDE_CODE_PROVIDER

log = get_logger(__name__)

# Потолок продуктового пути. Онбординг-триал навешивает свой, более жёсткий
# дедлайн (asyncio.timeout вокруг всего вызова) — этот страхует steady-state.
DEFAULT_TIMEOUT_SEC = 180.0


class ClaudeCodeError(Exception):
    """`claude -p` не смог выдать ответ: нет бинарника, не залогинен, ненулевой
    код возврата, таймаут или нераспарсиваемый вывод."""


def resolve_claude_binary() -> str | None:
    """Абсолютный путь к CLI `claude`, либо None. Бэкенд запускает Tauri —
    PATH может быть урезанным, поэтому падаем на известные места установки."""
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
    """Каталог без проектного CLAUDE.md / .claude/settings.json — чтобы
    сервер-спавн `claude -p` не подцепил конфиг репозитория."""
    root = AppPaths().root
    root.mkdir(parents=True, exist_ok=True)
    return str(root)


def _clean_env() -> dict[str, str]:
    """Окружение подпроцесса без ANTHROPIC_API_KEY — auth только из подписки."""
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    return env


def _text_of(content: Any) -> str:
    """Контент сообщения LiteLLM — строка (assistant) или список
    {type:'text', text:...} (user). Оба уплощаем в текст."""
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
    """Массив сообщений → (system_prompt, user_prompt) для `claude -p`.
    Все system-роли — в системный промпт; остальные ходы уплощаем в один
    текст с маркерами ролей (модель stateless — контекст живёт здесь)."""
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
    """LiteLLM-провайдер поверх установленного CLI Claude Code (`claude -p`) на
    подписке пользователя. Зарегистрирован под провайдером `claude-code`, так
    что deployment `model='claude-code/<alias>'` идёт через обычный Router
    AILayer — без ветки в AILayer, с единым фолбэком/стримом."""

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
            raise ClaudeCodeError("Claude Code CLI (`claude`) not found")
        system, prompt = _messages_to_prompt(messages)
        proc_args = self._base_args(binary, model, system, prompt) + [
            "--output-format",
            "json",
        ]
        proc = await self._spawn(proc_args)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
        except (asyncio.TimeoutError, TimeoutError) as exc:
            proc.kill()
            await proc.wait()
            raise ClaudeCodeError(
                f"`claude -p` timed out after {timeout:.0f}s"
            ) from exc
        if proc.returncode != 0:
            tail = stderr.decode(errors="replace")[-500:]
            raise ClaudeCodeError(f"`claude -p` exited {proc.returncode}: {tail}")
        try:
            data = json.loads(stdout.decode(errors="replace"))
        except json.JSONDecodeError as exc:
            raise ClaudeCodeError(
                f"`claude -p` returned non-JSON output: {exc}"
            ) from exc
        if data.get("is_error"):
            raise ClaudeCodeError(
                f"`claude -p` reported an error: {str(data.get('result', ''))[:300]}"
            )
        return self._to_response(model, data)

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
    """Идемпотентно регистрирует ClaudeCodeLLM под провайдером `claude-code`,
    чтобы LiteLLM маршрутизировал `model='claude-code/...'` в него."""
    for item in litellm.custom_provider_map:
        if item.get("provider") == CLAUDE_CODE_PROVIDER:
            return
    litellm.custom_provider_map = [
        *litellm.custom_provider_map,
        {"provider": CLAUDE_CODE_PROVIDER, "custom_handler": ClaudeCodeLLM()},
    ]
