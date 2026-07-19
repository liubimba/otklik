from collections.abc import Iterator

import httpx
import litellm
import pytest
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler

from otklik_backend.ai.error_hints import humanize_llm_error
from otklik_backend.ai.proxy import (
    _ORIGINAL_DISABLE_AIOHTTP,
    _ORIGINAL_TRANSPORT,
    apply_llm_proxy,
)


@pytest.fixture(autouse=True)
def restore_proxy() -> Iterator[None]:
    yield
    apply_llm_proxy(None)


async def test_apply_llm_proxy_routes_requests_through_the_proxy() -> None:
    apply_llm_proxy("socks5://127.0.0.1:1")

    transport = AsyncHTTPHandler._create_async_transport()
    assert isinstance(transport, httpx.AsyncHTTPTransport)

    async with httpx.AsyncClient(transport=transport) as httpclient:
        with pytest.raises(httpx.HTTPError):
            await httpclient.get("https://example.com", timeout=3)


def test_apply_llm_proxy_forces_httpx_transport() -> None:
    apply_llm_proxy("http://127.0.0.1:10809")
    assert litellm.disable_aiohttp_transport is True


def test_apply_llm_proxy_none_restores_the_default_transport() -> None:
    apply_llm_proxy("http://127.0.0.1:10809")

    apply_llm_proxy(None)

    assert AsyncHTTPHandler.__dict__["_create_async_transport"] is _ORIGINAL_TRANSPORT
    assert litellm.disable_aiohttp_transport is _ORIGINAL_DISABLE_AIOHTTP


def test_apply_llm_proxy_blank_is_treated_as_no_proxy() -> None:
    apply_llm_proxy("   ")
    assert AsyncHTTPHandler.__dict__["_create_async_transport"] is _ORIGINAL_TRANSPORT


def test_humanize_forbidden_points_to_the_proxy_setting() -> None:
    hint = humanize_llm_error(
        'litellm.APIError: GroqException - {"error":{"message":"Forbidden"}}'
    )
    assert "регион" in hint
    assert "прокси" in hint.lower() or "vpn" in hint.lower()


def test_humanize_connection_failure_points_to_the_proxy_setting() -> None:
    hint = humanize_llm_error("httpx.ConnectError: All connection attempts failed")
    assert "прокси" in hint.lower()


def test_humanize_gigachat_auth_error_explains_the_right_key() -> None:
    hint = humanize_llm_error(
        "GigachatException - GigaChat authentication failed: "
        '{"code":4,"message":"Can\'t decode \'Authorization\' header"}'
    )
    assert "GigaChat" in hint
    assert "авторизаци" in hint.lower()


def test_humanize_passes_through_unrelated_errors() -> None:
    assert humanize_llm_error("Rate limit exceeded") == "Rate limit exceeded"
