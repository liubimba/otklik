from unittest.mock import AsyncMock, patch

import httpx

from otklik_backend.setup.ollama import OllamaGate, OllamaState


def _gate() -> OllamaGate:
    return OllamaGate(host="http://localhost:11434", model_tag="qwen2.5:7b")


async def _state_with(
    *, binary: bool, tags_response: httpx.Response | Exception
) -> OllamaState:
    which = "/usr/bin/ollama" if binary else None
    with (
        patch("otklik_backend.setup.ollama.shutil.which", return_value=which),
        patch("otklik_backend.setup.ollama.httpx.AsyncClient") as client_cls,
    ):
        client = client_cls.return_value.__aenter__.return_value
        if isinstance(tags_response, Exception):
            client.get = AsyncMock(side_effect=tags_response)
        else:
            client.get = AsyncMock(return_value=tags_response)
        return await _gate().state()


def _tags(*names: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"models": [{"name": name} for name in names]},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )


async def test_not_installed_when_no_binary_and_no_server() -> None:
    state = await _state_with(binary=False, tags_response=httpx.ConnectError("refused"))
    assert state == OllamaState.NOT_INSTALLED


async def test_not_running_when_binary_present_but_server_silent() -> None:
    state = await _state_with(binary=True, tags_response=httpx.ConnectError("refused"))
    assert state == OllamaState.NOT_RUNNING


async def test_model_missing_when_server_answers_without_our_tag() -> None:
    state = await _state_with(binary=True, tags_response=_tags("llama3:8b"))
    assert state == OllamaState.MODEL_MISSING


async def test_ready_when_tag_present() -> None:
    state = await _state_with(
        binary=True, tags_response=_tags("llama3:8b", "qwen2.5:7b")
    )
    assert state == OllamaState.READY


async def test_ready_ignores_the_latest_suffix() -> None:
    # Ollama отдаёт теги как `qwen2.5:7b`, но пользователь мог тянуть
    # `qwen2.5:7b-instruct-q4_K_M` — это другая модель, совпадением не считаем.
    state = await _state_with(
        binary=True, tags_response=_tags("qwen2.5:7b-instruct-q4_K_M")
    )
    assert state == OllamaState.MODEL_MISSING


async def test_server_answering_without_binary_is_still_running() -> None:
    # Ollama может крутиться в Docker — бинаря на хосте нет, а сервер отвечает.
    state = await _state_with(binary=False, tags_response=_tags("qwen2.5:7b"))
    assert state == OllamaState.READY


async def test_timeout_is_treated_as_silent_server() -> None:
    state = await _state_with(binary=True, tags_response=httpx.ReadTimeout("slow"))
    assert state == OllamaState.NOT_RUNNING
