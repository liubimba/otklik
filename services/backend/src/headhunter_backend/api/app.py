from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.routes import (
    settings,
    ws,
    vacancies,
    letter,
    submission,
    auth,
    orchestrator,
    ai,
    rate_limits,
    applications,
    search,
)
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.log import configure_logging, get_logger
from headhunter_backend.orchestrator.authorization_service import AuthorizationService
from headhunter_backend.orchestrator.cover_letter_service import CoverLetterService
from headhunter_backend.orchestrator.queue import Orchestrator
from headhunter_backend.orchestrator.state_service import StateTransitionService
from headhunter_backend.db.session import session_maker, apply_sqlite_pragmas, engine
from headhunter_backend.browser.writer import BrowserWriter
from headhunter_backend.browser.selectors import HHRU_SELECTORS
from headhunter_backend.orchestrator.search import SearchService
from headhunter_backend.browser.parser import Parser
from headhunter_backend.api.schemas import SearchStatusAPISchema
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.db.models import SettingsORM
from typing import Any
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from headhunter_backend.orchestrator.apply_service import AutoApplyService
from headhunter_backend.api.errors import register_error_handlers
from headhunter_backend.db.repositories.search_history import SearchHistoryRepository
from headhunter_backend.db.repositories.settings import SettingsRepository

logger = get_logger(__name__)


async def bootstrap_ai_layer(maker: async_sessionmaker[AsyncSession]) -> AILayer:
    async with maker() as session:
        settings: SettingsORM = await SettingsRepository.get(session=session)
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
    app.state.state_service = StateTransitionService(broadcaster=app.state.broadcaster)
    app.state.orchestrator = Orchestrator(state_service=app.state.state_service)
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
    app.state.cover_letter_service = CoverLetterService(
        session_maker=session_maker,
        ai_layer=app.state.ai_layer,
        state_service=app.state.state_service,
    )
    app.state.apply_service = AutoApplyService(
        session_maker=session_maker,
        ai_layer=app.state.ai_layer,
        orchestrator=app.state.orchestrator,
    )
    app.state.authorization_service = AuthorizationService(
        broadcaster=app.state.broadcaster, core=app.state.browser
    )
    app.state.apply_service.start(broadcaster=app.state.broadcaster)
    async with session_maker() as session:
        recovered_count: int = await app.state.orchestrator.recover_from_db(
            session=session
        )
        await app.state.cover_letter_service.recover_pending(session=session)
        for search_history in await SearchHistoryRepository.list_all(session=session):
            if search_history.status.is_active():
                await SearchHistoryRepository.update(
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
router.include_router(letter.letter_router)
router.include_router(submission.submission_router)
router.include_router(settings.settings_router)
router.include_router(auth.user_router)
router.include_router(orchestrator.orchestrator_router)
router.include_router(ai.ai_router)
router.include_router(rate_limits.rate_limits_router)
router.include_router(applications.applications_router)
router.include_router(search.search_router)

app = FastAPI(title="Headhunter Backend API", version="0.0.1", lifespan=lifespan)
app.include_router(router)
app.include_router(ws.ws_router)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
register_error_handlers(app=app)


def run() -> None:
    import uvicorn

    uvicorn.run("headhunter_backend.api.app:app", host="127.0.0.1", port=8001)
