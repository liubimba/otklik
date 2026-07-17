import json
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from otklik_backend.log import get_logger
from otklik_backend.secrets.store import (
    SecretStore,
    SecretStoreUnavailableError,
    account_for,
)


class SecretMigrator:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        engine: AsyncEngine,
        store: SecretStore,
    ) -> None:
        self._session_maker = session_maker
        self._engine = engine
        self._store = store
        self._log = get_logger(self.__class__.__name__)

    async def migrate(self) -> None:
        entries = await self._read_raw()
        if entries is None or not self._needs_migration(entries):
            return
        try:
            to_move: list[tuple[str, str]] = []
            for entry in entries:
                entry.setdefault("id", uuid4().hex)
                key = entry.get("api_key")
                entry["has_api_key"] = bool(key) or bool(
                    entry.get("has_api_key", False)
                )
                if key:
                    to_move.append((account_for(str(entry["id"])), str(key)))
            await self._write_raw(entries)

            moved = 0
            for account, secret in to_move:
                await self._store.set(account, secret)
                moved += 1

            for entry in entries:
                entry.pop("api_key", None)
            await self._write_raw(entries)
        except SecretStoreUnavailableError as e:
            self._log.warning(
                "Секретное хранилище недоступно, повторим на следующем старте: %s", e
            )
            return
        except Exception as e:
            self._log.error("Неожиданный сбой SecretMigrator'а: %s", e)
            return
        if moved:
            self._log.info("Moved LLM keys out of the database", count=moved)
            await self._scrub()

    @staticmethod
    def _needs_migration(entries: list[dict[str, Any]]) -> bool:
        return any(
            "api_key" in entry or "id" not in entry or "has_api_key" not in entry
            for entry in entries
        )

    async def _read_raw(self) -> list[dict[str, Any]] | None:
        async with self._session_maker() as session:
            result = await session.execute(
                text("SELECT llm_deployments FROM settings WHERE id = 1")
            )
            raw = result.scalar_one_or_none()
        if raw is None:
            return None
        loaded: Any = json.loads(raw) if isinstance(raw, str) else raw
        return loaded if isinstance(loaded, list) else None

    async def _write_raw(self, entries: list[dict[str, Any]]) -> None:
        async with self._session_maker() as session:
            await session.execute(
                text("UPDATE settings SET llm_deployments = :value WHERE id = 1"),
                {"value": json.dumps(entries)},
            )
            await session.commit()

    async def _scrub(self) -> None:
        async with self._engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
            await conn.exec_driver_sql("VACUUM")
