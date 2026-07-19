from collections.abc import Iterator

import httpx
import pytest
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler

from otklik_backend.ai.error_hints import humanize_llm_error
from otklik_backend.ai.proxy import _resolve_verify, apply_llm_proxy


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


def test_ssl_verify_false_yields_a_fresh_httpx_transport_without_proxy() -> None:
    apply_llm_proxy(None)
    transport = AsyncHTTPHandler._create_async_transport(ssl_verify=False)
    assert isinstance(transport, httpx.AsyncHTTPTransport)


def test_normal_requests_keep_the_default_transport_without_proxy() -> None:
    apply_llm_proxy(None)
    transport = AsyncHTTPHandler._create_async_transport()
    assert not isinstance(transport, httpx.AsyncHTTPTransport)


def test_resolve_verify_maps_ssl_verify_false_to_no_verification() -> None:
    assert _resolve_verify(None, False) is False
    assert _resolve_verify(None, None) is True
    assert _resolve_verify(None, True) is True


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
