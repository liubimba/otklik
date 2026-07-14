import shutil
from enum import Enum
from typing import Any

import httpx

from otklik_backend.log import get_logger
from otklik_backend.setup.constants import LOCAL_MODEL_TAG, OLLAMA_HOST

TAGS_TIMEOUT_SEC = 2.0


class OllamaState(str, Enum):
    NOT_INSTALLED = "not_installed"
    NOT_RUNNING = "not_running"
    MODEL_MISSING = "model_missing"
    READY = "ready"


class OllamaGate:
    """Разговор с локальной Ollama по HTTP.

    Состояние определяется по живому ответу сервера, а не по факту установки
    бинарника: установленная, но не запущенная Ollama так же бесполезна, как
    отсутствующая, и пользователю надо сказать разное. Различаем их так:
    сервер молчит + бинарь есть → «не запущена»; сервер молчит и бинаря нет →
    «не установлена». Сервер, отвечающий без бинаря на хосте (Ollama в Docker),
    считается работающим.

    Сервис из приложения НЕ поднимаем — это OS-специфично и рискованно
    (решение зафиксировано в спеке).
    """

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

    async def _list_tags(self) -> list[str] | None:
        """Теги установленных моделей, либо None, если сервер не отвечает."""
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
                # {"models": null} — сервер отвечает странно
                return None
            return [str(model["name"]) for model in models]
        except (TypeError, AttributeError, KeyError) as error:
            # payload не словарь, или models не список, или элемент без "name"
            self._log.info(
                "Ollama response has unexpected format on %s: %s", self._host, error
            )
            return None
