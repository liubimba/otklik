from pathlib import Path
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from typing import AsyncIterator
from sqlalchemy import event
from typing import Any

DB_PATH = Path.home() / ".headhunter_ai" / "db.sqlite"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


def ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _py_lower(value: str | None) -> str | None:
    return value.lower() if value is not None else None


def _set_sqlite_params(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()

    # SQLite's built-in lower()/LIKE only case-fold ASCII, so "разработчик"
    # would not match "Разработчик". Push the fold through Python's str.lower,
    # which is Unicode-aware. Deterministic, so SQLite may use it in indexes.
    dbapi_connection.create_function("py_lower", 1, _py_lower, deterministic=True)


def apply_sqlite_pragmas(target_engine: AsyncEngine) -> None:
    event.listen(target_engine.sync_engine, "connect", _set_sqlite_params)


engine: AsyncEngine = create_async_engine(url=DATABASE_URL)

# Attach here, not in the FastAPI lifespan. The hook runs on `connect`, so any
# connection opened before it is registered is pooled unconfigured — and
# AsyncAdaptedQueuePool hands that same connection to every later request.
apply_sqlite_pragmas(target_engine=engine)

session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session
