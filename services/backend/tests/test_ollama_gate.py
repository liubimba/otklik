from unittest.mock import AsyncMock, patch

import httpx
import pytest

from otklik_backend.setup.ollama import (
    OllamaGate,
    OllamaState,
    OllamaPullError,
)


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


async def test_tag_with_extra_suffix_is_a_different_model() -> None:
    state = await _state_with(
        binary=True, tags_response=_tags("qwen2.5:7b-instruct-q4_K_M")
    )
    assert state == OllamaState.MODEL_MISSING


async def test_server_answering_without_binary_is_still_running() -> None:
    state = await _state_with(binary=False, tags_response=_tags("qwen2.5:7b"))
    assert state == OllamaState.READY


async def test_timeout_is_treated_as_silent_server() -> None:
    state = await _state_with(binary=True, tags_response=httpx.ReadTimeout("slow"))
    assert state == OllamaState.NOT_RUNNING


async def test_models_null_is_treated_as_silent_server() -> None:
    response = httpx.Response(
        200,
        json={"models": None},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )
    state = await _state_with(binary=True, tags_response=response)
    assert state == OllamaState.NOT_RUNNING


async def test_top_level_array_is_treated_as_malformed() -> None:
    response = httpx.Response(
        200,
        json=[{"name": "qwen2.5:7b"}],
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )
    state = await _state_with(binary=True, tags_response=response)
    assert state == OllamaState.NOT_RUNNING


async def test_model_entry_without_name_is_treated_as_malformed() -> None:
    response = httpx.Response(
        200,
        json={"models": [{"size": 123}]},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )
    state = await _state_with(binary=True, tags_response=response)
    assert state == OllamaState.NOT_RUNNING


async def test_empty_models_list_means_model_missing() -> None:
    state = await _state_with(binary=True, tags_response=_tags())
    assert state == OllamaState.MODEL_MISSING


class _FakeStream:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


async def _pull_with(lines: list[str]):
    with patch("otklik_backend.setup.ollama.httpx.AsyncClient") as client_cls:
        client = client_cls.return_value.__aenter__.return_value
        client.stream = lambda *a, **kw: _FakeStream(lines)
        return [progress async for progress in _gate().pull()]


async def test_pull_reports_real_percentages() -> None:
    events = await _pull_with(
        [
            '{"status":"pulling manifest"}',
            '{"status":"downloading","completed":1000,"total":4000}',
            '{"status":"downloading","completed":4000,"total":4000}',
            '{"status":"success"}',
        ]
    )
    assert [round(e.percent) for e in events] == [0, 25, 100, 100]
    assert events[-1].done is True
    assert events[1].completed_bytes == 1000
    assert events[1].total_bytes == 4000


async def test_pull_skips_blank_lines() -> None:
    events = await _pull_with(['{"status":"success"}', "", "   "])
    assert len(events) == 1


async def test_pull_raises_on_server_error() -> None:
    events_source = '{"error":"no space left on device"}'
    with pytest.raises(OllamaPullError, match="no space left on device"):
        await _pull_with([events_source])


class _FakeStreamWithHTTPError:
    def __init__(self, status_code: int = 500) -> None:
        self._status_code = status_code

    async def __aenter__(self) -> "_FakeStreamWithHTTPError":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        response = httpx.Response(
            self._status_code,
            request=httpx.Request("POST", "http://localhost:11434/api/pull"),
        )
        response.raise_for_status()

    async def aiter_lines(self):
        yield ""


async def test_pull_raises_on_http_error_500() -> None:
    with patch("otklik_backend.setup.ollama.httpx.AsyncClient") as client_cls:
        client = client_cls.return_value.__aenter__.return_value
        client.stream = lambda *a, **kw: _FakeStreamWithHTTPError(status_code=500)
        with pytest.raises(OllamaPullError, match="Failed to pull model"):
            [progress async for progress in _gate().pull()]


async def test_pull_raises_on_http_error_404() -> None:
    with patch("otklik_backend.setup.ollama.httpx.AsyncClient") as client_cls:
        client = client_cls.return_value.__aenter__.return_value
        client.stream = lambda *a, **kw: _FakeStreamWithHTTPError(status_code=404)
        with pytest.raises(OllamaPullError, match="Failed to pull model"):
            [progress async for progress in _gate().pull()]


async def test_pull_raises_on_malformed_json() -> None:
    with pytest.raises(OllamaPullError, match="Invalid JSON in response"):
        await _pull_with(['{"status":"downloading"', '{"status":"success"}'])


async def test_pull_raises_on_null_completed() -> None:
    with pytest.raises(OllamaPullError, match="Invalid response format"):
        await _pull_with(['{"status":"downloading","completed":null,"total":4000}'])


async def test_pull_raises_on_null_total() -> None:
    with pytest.raises(OllamaPullError, match="Invalid response format"):
        await _pull_with(['{"status":"downloading","completed":1000,"total":null}'])


async def _list_models_with(tags_response: httpx.Response | Exception) -> list[str]:
    with patch("otklik_backend.setup.ollama.httpx.AsyncClient") as client_cls:
        client = client_cls.return_value.__aenter__.return_value
        if isinstance(tags_response, Exception):
            client.get = AsyncMock(side_effect=tags_response)
        else:
            client.get = AsyncMock(return_value=tags_response)
        return await _gate().list_models()


async def test_list_models_returns_installed_tags() -> None:
    models = await _list_models_with(_tags("qwen2.5:7b", "llama3:8b"))
    assert models == ["qwen2.5:7b", "llama3:8b"]


async def test_list_models_is_empty_when_server_silent() -> None:
    models = await _list_models_with(httpx.ConnectError("refused"))
    assert models == []


async def test_list_models_is_empty_on_malformed_payload() -> None:
    bad = httpx.Response(
        200,
        json={"models": None},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )
    models = await _list_models_with(bad)
    assert models == []
