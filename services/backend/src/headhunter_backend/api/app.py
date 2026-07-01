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
from headhunter_backend.orchestrator.listeners.auto_submit import AutoSubmitListener
from headhunter_backend.orchestrator.state_service import StateTransitionService
from headhunter_backend.orchestrator.workers.letter_pending import LetterPendingWorker
from headhunter_backend.orchestrator.workers.letter_sending import LetterSendingWorker
from headhunter_backend.db.session import session_maker, apply_sqlite_pragmas, engine
from headhunter_backend.browser.writer import BrowserWriter
from headhunter_backend.orchestrator.search import SearchService
from headhunter_backend.sites.hh_ru import HHRUParser, HHRU_SELECTORS
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
    app.state.writer = BrowserWriter(
        core=app.state.browser, min_delay_ms=800, jitter_delay_ms=400
    )
    app.state.search_service = SearchService(
        core=app.state.browser,
        parser=HHRUParser(core=app.state.browser),
        broadcaster=app.state.broadcaster,
        session_maker=session_maker,
        selectors=HHRU_SELECTORS,
    )
    app.state.orchestrator = LetterSendingWorker(
        state_service=app.state.state_service,
        session_maker=session_maker,
        browser=app.state.browser,
        writer=app.state.writer,
        broadcaster=app.state.broadcaster,
        selectors=HHRU_SELECTORS,
    )
    app.state.orchestrator.start()
    app.state.ai_layer = await bootstrap_ai_layer(maker=session_maker)
    app.state.cover_letter_service = CoverLetterService(
        session_maker=session_maker,
        ai_layer=app.state.ai_layer,
        state_service=app.state.state_service,
    )
    app.state.letter_pending_worker = LetterPendingWorker(
        cover_letter_service=app.state.cover_letter_service,
        state_service=app.state.state_service,
        session_maker=session_maker,
        broadcaster=app.state.broadcaster,
    )
    app.state.letter_pending_worker.start()
    app.state.auto_submit_listener = AutoSubmitListener(
        state_service=app.state.state_service,
        session_maker=session_maker,
        broadcaster=app.state.broadcaster,
    )
    app.state.auto_submit_listener.start()
    app.state.apply_service = AutoApplyService(
        session_maker=session_maker,
        state_service=app.state.state_service,
    )
    app.state.authorization_service = AuthorizationService(
        broadcaster=app.state.broadcaster, core=app.state.browser
    )
    app.state.apply_service.start(broadcaster=app.state.broadcaster)
    async with session_maker() as session:
        recovered_count: int = await app.state.orchestrator.recover(session=session)
        pending_count = await app.state.letter_pending_worker.recover(session=session)
        ready_count = await app.state.auto_submit_listener.recover(session=session)
        for search_history in await SearchHistoryRepository.list_all(session=session):
            if search_history.status.is_active():
                await SearchHistoryRepository.update(
                    session=session,
                    search_id=search_history.id,
                    finished_at=datetime.now(),
                    status=SearchStatusAPISchema.INTERRUPTED,
                )

        logger.info(
            "Recovery complete",
            sending=recovered_count,
            pending=pending_count,
            ready_resubmitted=ready_count,
        )

    apply_sqlite_pragmas(target_engine=engine)
    await app.state.browser.start()

    consumer_task = asyncio.create_task(app.state.orchestrator.run())
    letter_task = asyncio.create_task(app.state.letter_pending_worker.run())

    try:
        yield
    finally:
        consumer_task.cancel()
        letter_task.cancel()
        app.state.orchestrator.stop()
        app.state.letter_pending_worker.stop()
        app.state.auto_submit_listener.stop()
        app.state.apply_service.stop()
        await app.state.search_service.shutdown()
        for task in (consumer_task, letter_task):
            try:
                await task
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
