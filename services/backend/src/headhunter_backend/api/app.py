from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.routes import settings, ws, vacancies, auth
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.log import configure_logging, get_logger
from typing import Any


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    configure_logging()
    logger = get_logger(__name__)
    logger.info("Starting Headhunter AI Backend API")
    app.state.browser = BrowserCore()
    app.state.broadcaster = EventBroadcaster()
    await app.state.browser.start()
    try:
        yield
    finally:
        await app.state.browser.stop()
    logger.info("Shutting down Headhunter AI Backend API")


router = APIRouter(prefix="/api/v1")
router.include_router(vacancies.vacancies_router)
router.include_router(settings.settings_router)
router.include_router(auth.auth_router)

app = FastAPI(title="Headhunter Backend API", version="0.0.1", lifespan=lifespan)
app.include_router(router)
app.include_router(ws.ws_router)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def run() -> None:
    import uvicorn

    uvicorn.run("headhunter_backend.api.app:app", host="127.0.0.1", port=8001)
