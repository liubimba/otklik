import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from otklik_backend.api.errors import register_error_handlers
from otklik_backend.api.routes import (
    application,
    auth,
    search,
    settings,
    setup,
    system,
    vacancies,
    ws,
)
from otklik_backend.api.schemas import SearchStatusAPISchema
from otklik_backend.core.builder import BackendBuilder
from otklik_backend.db.repositories.search_history import SearchHistoryRepository
from otklik_backend.db.session import engine, ensure_db_dir, session_maker
from otklik_backend.log import configure_logging, get_logger

logger = get_logger(__name__)

# Бэкенд слушает 127.0.0.1 без авторизации, поэтому "*" означал: ЛЮБАЯ открытая
# вкладка в браузере может читать наши ответы и дёргать наши ручки. Сужаем до
# origin'ов самого приложения: devUrl из tauri.conf.json и origin'ы webview в
# собранном билде (tauri://localhost на macOS/Linux, http://tauri.localhost на Windows).
#
# Граница честности: CORS проверяется браузером, а не нами — он закрывает вектор
# "вредоносная вкладка читает fetch() к 127.0.0.1:8001", но не защищает от
# локального процесса. Локальный процесс может напрямую прочитать
# ~/.otklik/secrets.json или дождаться системного диалога кейчейна — это вне
# зоны ответственности CORS.
ALLOWED_ORIGINS = [
    "http://localhost:1420",
    "tauri://localhost",
    "http://tauri.localhost",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    configure_logging()
    logger.info("Starting Otklik Backend API")
    # Adopts ~/.headhunter_ai from installs predating the rename, before any
    # component can touch the database.
    ensure_db_dir()
    ctx = await BackendBuilder(session_maker=session_maker, engine=engine).build()
    for attr, value in ctx.__dict__.items():
        setattr(app.state, attr, value)

    for component in ctx.event_listeners():
        component.start()

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

    await ctx.browser.start()

    tasks = [asyncio.create_task(r.run()) for r in ctx.runnables()]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for component in ctx.event_listeners():
            component.stop()
        await ctx.search_service.shutdown()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        await ctx.browser.stop()
    logger.info("Shutting down Otklik Backend API")


router = APIRouter(prefix="/api/v1")
router.include_router(vacancies.vacancies_router)
router.include_router(application.application_router)
router.include_router(application.applications_router)
router.include_router(auth.auth_router)
router.include_router(search.search_router)
router.include_router(settings.settings_router)
router.include_router(setup.setup_router)
router.include_router(system.system_router)

app = FastAPI(title="Otklik Backend API", version="0.0.1", lifespan=lifespan)
app.include_router(router)
app.include_router(ws.ws_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app=app)


def run() -> None:
    import uvicorn

    uvicorn.run("otklik_backend.api.app:app", host="127.0.0.1", port=8001)
