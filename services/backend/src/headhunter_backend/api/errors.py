from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from headhunter_backend.exceptions import ServerError
from headhunter_backend.log import get_logger

_log = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServerError)
    async def _handle_server_error(
        request: Request, exception: ServerError
    ) -> JSONResponse:
        _log.exception("Server error", path=request.url.path)
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": exception.detail},
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
