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
        folded = (
            await conn.execute(text("SELECT py_lower('РазРАБотчик')"))
        ).scalar_one()
        assert folded == "разработчик"

    await target.dispose()


async def test_connection_opened_before_the_hook_is_never_configured(tmp_path) -> None:
    target = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'early.sqlite'}")

    async with target.connect() as conn:
        await conn.execute(text("SELECT 1"))

    apply_sqlite_pragmas(target_engine=target)

    async with target.connect() as conn:
        assert (await conn.execute(text("PRAGMA journal_mode"))).scalar_one() != "wal"
        with pytest.raises(OperationalError):
            await conn.execute(text("SELECT py_lower('x')"))

    await target.dispose()


def test_app_engine_is_configured_at_import() -> None:
    assert event.contains(engine.sync_engine, "connect", _set_sqlite_params)
