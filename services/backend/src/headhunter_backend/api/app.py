import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from headhunter_backend.api.errors import register_error_handlers
from headhunter_backend.api.routes import (
    application,
    auth,
    search,
    settings,
    system,
    vacancies,
    ws,
)
from headhunter_backend.api.schemas import SearchStatusAPISchema
from headhunter_backend.core.builder import BackendBuilder
from headhunter_backend.db.repositories.search_history import SearchHistoryRepository
from headhunter_backend.db.session import apply_sqlite_pragmas, engine, session_maker
from headhunter_backend.log import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    configure_logging()
    logger.info("Starting Headhunter AI Backend API")
    ctx = await BackendBuilder(session_maker=session_maker).build()
    for attr, value in ctx.__dict__.items():
        setattr(app.state, attr, value)

    for component in ctx.event_listeners():
        component.start()
    ctx.apply_service.start(broadcaster=ctx.broadcaster)

    async with session_maker() as session:
        for recoverable in ctx.recoverables():
            await recoverable.recover(session=session)
        for search_history in await SearchHistoryRepository.list_all(session=session):
            if search_history.status.is_active():
                await SearchHistoryRepository.update(
                    session=session,
                    search_id=search_history.id,
                    finished_at=datetime.now(),
                    status=SearchStatusAPISchema.INTERRUPTED,
                )
    logger.info("Recovery complete")

    apply_sqlite_pragmas(target_engine=engine)
    await ctx.browser.start()

    tasks = [asyncio.create_task(r.run()) for r in ctx.runnables()]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for component in ctx.event_listeners():
            component.stop()
        ctx.apply_service.stop()
        await ctx.search_service.shutdown()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        await ctx.browser.stop()
    logger.info("Shutting down Headhunter AI Backend API")


router = APIRouter(prefix="/api/v1")
router.include_router(vacancies.vacancies_router)
router.include_router(application.application_router)
router.include_router(auth.auth_router)
router.include_router(search.search_router)
router.include_router(settings.settings_router)
router.include_router(system.system_router)

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
