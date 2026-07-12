"""The SQLite connect-hook: WAL, foreign keys, and the Unicode-aware py_lower()
UDF that free-text vacancy search depends on.

All three are attached on `connect`, so they only reach connections opened after
the listener is registered. `AsyncAdaptedQueuePool` then hands the very first
(unconfigured) connection back to later callers — hence the ordering test below.
"""

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from otklik_backend.db.session import (
    _set_sqlite_params,
    apply_sqlite_pragmas,
    engine,
)


async def test_pragma_hook_configures_a_connection(tmp_path) -> None:
    target = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'hook.sqlite'}")
    apply_sqlite_pragmas(target_engine=target)

    async with target.connect() as conn:
        assert (await conn.execute(text("PRAGMA journal_mode"))).scalar_one() == "wal"
        assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one() == 1
        # SQLite's built-in lower() only folds ASCII.
        folded = (
            await conn.execute(text("SELECT py_lower('РазРАБотчик')"))
        ).scalar_one()
        assert folded == "разработчик"

    await target.dispose()


async def test_connection_opened_before_the_hook_is_never_configured(tmp_path) -> None:
    """Why the hook must be attached before anything touches the DB: a
    connection checked out earlier is pooled unconfigured and reused forever."""
    target = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'early.sqlite'}")

    async with target.connect() as conn:
        await conn.execute(text("SELECT 1"))  # pools an unconfigured connection

    apply_sqlite_pragmas(target_engine=target)

    async with target.connect() as conn:
        assert (await conn.execute(text("PRAGMA journal_mode"))).scalar_one() != "wal"
        with pytest.raises(OperationalError):
            await conn.execute(text("SELECT py_lower('x')"))

    await target.dispose()


def test_app_engine_is_configured_at_import() -> None:
    """Regression: the app used to call apply_sqlite_pragmas() inside the FastAPI
    lifespan, *after* startup recovery had already opened a session. Every later
    request reused that unconfigured connection, so vacancy search died on
    `no such function: py_lower`. Attaching at import makes the order unmissable."""
    assert event.contains(engine.sync_engine, "connect", _set_sqlite_params)
