import json
import shutil
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel

from otklik_backend.log import get_logger
from otklik_backend.setup.constants import LOCAL_MODEL_TAG, OLLAMA_HOST

TAGS_TIMEOUT_SEC = 2.0
PULL_TIMEOUT_SEC = 60.0


class OllamaPullError(Exception): ...


class PullProgress(BaseModel):
    status: str
    completed_bytes: int = 0
    total_bytes: int = 0
    percent: float = 0.0
    done: bool = False


class OllamaState(str, Enum):
    NOT_INSTALLED = "not_installed"
    NOT_RUNNING = "not_running"
    MODEL_MISSING = "model_missing"
    READY = "ready"


class OllamaGate:
    def __init__(
        self, host: str = OLLAMA_HOST, model_tag: str = LOCAL_MODEL_TAG
    ) -> None:
        self._host = host
        self._model_tag = model_tag
        self._log = get_logger(__name__)

    async def state(self) -> OllamaState:
        tags: list[str] | None = await self._list_tags()
        if tags is None:
            return (
                OllamaState.NOT_RUNNING
                if shutil.which("ollama") is not None
                else OllamaState.NOT_INSTALLED
            )
        return (
            OllamaState.READY if self._model_tag in tags else OllamaState.MODEL_MISSING
        )

    async def list_models(self) -> list[str]:
        return await self._list_tags() or []

    async def _list_tags(self) -> list[str] | None:
        try:
            async with httpx.AsyncClient(timeout=TAGS_TIMEOUT_SEC) as client:
                response = await client.get(f"{self._host}/api/tags")
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except (httpx.HTTPError, ValueError) as error:
            self._log.info("Ollama is not answering on %s: %s", self._host, error)
            return None

        try:
            models = payload.get("models", [])
            if models is None:
                return None
            return [str(model["name"]) for model in models]
        except (TypeError, AttributeError, KeyError) as error:
            self._log.info(
                "Ollama response has unexpected format on %s: %s", self._host, error
            )
            return None

    async def pull(self) -> AsyncIterator[PullProgress]:
        async with httpx.AsyncClient(timeout=PULL_TIMEOUT_SEC) as client:
            async with client.stream(
                "POST",
                f"{self._host}/api/pull",
                json={"model": self._model_tag, "stream": True},
            ) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPError as error:
                    raise OllamaPullError(f"Failed to pull model: {error}") from error

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        event: dict[str, Any] = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise OllamaPullError(
                            f"Invalid JSON in response: {error}"
                        ) from error

                    if "error" in event:
                        raise OllamaPullError(str(event["error"]))

                    try:
                        yield self._to_progress(event)
                    except (TypeError, ValueError) as error:
                        raise OllamaPullError(
                            f"Invalid response format: {error}"
                        ) from error

    @staticmethod
    def _to_progress(event: dict[str, Any]) -> PullProgress:
        status = str(event.get("status", ""))
        completed_raw = event.get("completed", 0)
        total_raw = event.get("total", 0)

        if completed_raw is None or total_raw is None:
            raise TypeError(
                f"Null value in response: completed={completed_raw}, "
                f"total={total_raw}"
            )

        completed = int(completed_raw)
        total = int(total_raw)
        done = status == "success"
        percent = 100.0 if done else (completed / total * 100 if total else 0.0)
        return PullProgress(
            status=status,
            completed_bytes=completed,
            total_bytes=total,
            percent=round(percent, 1),
            done=done,
        )
