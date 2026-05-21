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


engine: AsyncEngine = create_async_engine(url=DATABASE_URL)


def _set_sqlite_params(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def apply_sqlite_pragmas(target_engine: AsyncEngine) -> None:
    event.listen(target_engine.sync_engine, "connect", _set_sqlite_params)


session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session
