from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.routes import (
    settings,
    ws,
    vacancies,
    auth,
    orchestrator,
    ai,
)
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.log import configure_logging, get_logger
from headhunter_backend.orchestrator.queue import Orchestrator
from headhunter_backend.db.session import session_maker, apply_sqlite_pragmas, engine
from headhunter_backend.browser.writer import BrowserWriter
from headhunter_backend.browser.selectors import HHRU_SELECTORS
from headhunter_backend.orchestrator.search import SearchService
from headhunter_backend.browser.parser import Parser
from headhunter_backend.db.crud import (
    list_search_history,
    update_search_history,
    get_settings,
)
from headhunter_backend.api.schemas import SearchStatusAPISchema
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.db.models import SettingsORM
from typing import Any
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = get_logger(__name__)


async def bootstrap_ai_layer(maker: async_sessionmaker[AsyncSession]) -> AILayer:
    async with maker() as session:
        settings: SettingsORM = await get_settings(session=session)
    try:
        return AILayer(deployments=settings.llm_deployments)
    except Exception as e:
        logger.error(
            "Failed to initialize AI Layer with error: %s. Initializing with no deployments.",
            str(e),
        )
        return AILayer()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    configure_logging()
    logger.info("Starting Headhunter AI Backend API")
    app.state.browser = BrowserCore()
    app.state.broadcaster = EventBroadcaster()
    app.state.orchestrator = Orchestrator()
    app.state.writer = BrowserWriter(
        core=app.state.browser, min_delay_ms=800, jitter_delay_ms=400
    )
    app.state.search_service = SearchService(
        core=app.state.browser,
        parser=Parser(core=app.state.browser),
        broadcaster=app.state.broadcaster,
        session_maker=session_maker,
        selectors=HHRU_SELECTORS,
    )
    app.state.ai_layer = await bootstrap_ai_layer(maker=session_maker)
    async with session_maker() as session:
        recovered_count: int = await app.state.orchestrator.recover_from_db(
            session=session
        )
        for search_history in await list_search_history(session=session):
            if search_history.status.is_active():
                await update_search_history(
                    session=session,
                    search_id=search_history.id,
                    finished_at=datetime.now(),
                    status=SearchStatusAPISchema.INTERRUPTED,
                )
        logger.info(f"Recovered {recovered_count} applications from the database.")
    apply_sqlite_pragmas(target_engine=engine)
    await app.state.browser.start()

    consumer_task = asyncio.create_task(
        app.state.orchestrator.consume(
            writer=app.state.writer,
            session_maker=session_maker,
            browser=app.state.browser,
            broadcaster=app.state.broadcaster,
            selectors=HHRU_SELECTORS,
        )
    )

    try:
        yield
    finally:
        consumer_task.cancel()
        await app.state.search_service.shutdown()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        await app.state.browser.stop()
    logger.info("Shutting down Headhunter AI Backend API")


router = APIRouter(prefix="/api/v1")
router.include_router(vacancies.vacancies_router)
router.include_router(settings.settings_router)
router.include_router(auth.auth_router)
router.include_router(orchestrator.orchestrator_router)
router.include_router(ai.ai_router)

app = FastAPI(title="Headhunter Backend API", version="0.0.1", lifespan=lifespan)
app.include_router(router)
app.include_router(ws.ws_router)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def run() -> None:
    import uvicorn

    uvicorn.run("headhunter_backend.api.app:app", host="127.0.0.1", port=8001)
