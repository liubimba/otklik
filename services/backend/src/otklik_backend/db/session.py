from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from typing import AsyncIterator
from sqlalchemy import event
from typing import Any

from otklik_backend.paths import AppPaths, DataDirMigrator

DB_PATH = AppPaths().db_file
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


def ensure_db_dir() -> None:
    DataDirMigrator().migrate()
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

    dbapi_connection.create_function("py_lower", 1, _py_lower, deterministic=True)


def apply_sqlite_pragmas(target_engine: AsyncEngine) -> None:
    event.listen(target_engine.sync_engine, "connect", _set_sqlite_params)


engine: AsyncEngine = create_async_engine(url=DATABASE_URL)

apply_sqlite_pragmas(target_engine=engine)

session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session
