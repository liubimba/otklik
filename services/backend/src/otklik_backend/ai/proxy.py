import ssl
from typing import Any, Optional

import httpx
import litellm
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler

from otklik_backend.log import get_logger

_log = get_logger(__name__)

_ORIGINAL_TRANSPORT = AsyncHTTPHandler._create_async_transport


def _resolve_verify(
    ssl_context: Optional[ssl.SSLContext], ssl_verify: Optional[bool]
) -> ssl.SSLContext | bool:
    if ssl_context is not None:
        return ssl_context
    if ssl_verify is False:
        return False
    return True


def apply_llm_proxy(proxy_url: str | None) -> None:
    from otklik_backend.ai.claude_code import set_claude_proxy

    proxy = (proxy_url or "").strip() or None
    set_claude_proxy(proxy)
    _flush_client_cache()

    def _transport(
        ssl_context: Optional[ssl.SSLContext] = None,
        ssl_verify: Optional[bool] = None,
        shared_session: Any = None,
    ) -> Any:
        if proxy is not None:
            return httpx.AsyncHTTPTransport(
                proxy=proxy, verify=_resolve_verify(ssl_context, ssl_verify)
            )
        if ssl_verify is False:
            return httpx.AsyncHTTPTransport(verify=False)
        return _ORIGINAL_TRANSPORT(
            ssl_context=ssl_context,
            ssl_verify=ssl_verify,
            shared_session=shared_session,
        )

    AsyncHTTPHandler._create_async_transport = staticmethod(_transport)  # type: ignore[method-assign]
    if proxy is not None:
        _log.info("LLM requests routed through proxy")


def _flush_client_cache() -> None:
    try:
        litellm.in_memory_llm_clients_cache.flush_cache()  # type: ignore[no-untyped-call]
    except Exception:  # noqa: BLE001
        pass
