from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from otklik_backend.core.exceptions import DomainError
from otklik_backend.log import get_logger

_log = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(
        request: Request, exception: DomainError
    ) -> JSONResponse:
        _log.exception(
            "Domain error",
            path=request.url.path,
            code=exception.code,
        )
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": exception.detail, "code": exception.code},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(
        request: Request, exception: Exception
    ) -> JSONResponse:
        _log.exception("Unhandled error", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
