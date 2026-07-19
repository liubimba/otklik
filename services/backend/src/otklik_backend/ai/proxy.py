import ssl
from typing import Optional

import httpx
import litellm
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler

from otklik_backend.log import get_logger

_log = get_logger(__name__)

_ORIGINAL_TRANSPORT = AsyncHTTPHandler.__dict__["_create_async_transport"]
_ORIGINAL_DISABLE_AIOHTTP = litellm.disable_aiohttp_transport


def apply_llm_proxy(proxy_url: str | None) -> None:
    normalized = (proxy_url or "").strip()
    _flush_client_cache()
    if not normalized:
        AsyncHTTPHandler._create_async_transport = _ORIGINAL_TRANSPORT  # type: ignore[method-assign]
        litellm.disable_aiohttp_transport = _ORIGINAL_DISABLE_AIOHTTP
        return

    litellm.disable_aiohttp_transport = True

    def _proxied_transport(
        ssl_context: Optional[ssl.SSLContext] = None,
        ssl_verify: Optional[bool] = None,
        shared_session: object = None,
    ) -> httpx.AsyncHTTPTransport:
        verify: ssl.SSLContext | bool
        if ssl_context is not None:
            verify = ssl_context
        elif ssl_verify is False:
            verify = False
        else:
            verify = True
        return httpx.AsyncHTTPTransport(proxy=normalized, verify=verify)

    AsyncHTTPHandler._create_async_transport = staticmethod(_proxied_transport)  # type: ignore[method-assign]
    _log.info("LLM requests routed through proxy")


def _flush_client_cache() -> None:
    try:
        litellm.in_memory_llm_clients_cache.flush_cache()  # type: ignore[no-untyped-call]
    except Exception:  # noqa: BLE001
        pass
