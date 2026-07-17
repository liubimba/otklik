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
    """Переносит ключи из открытой JSON-колонки в хранилище и вычищает их из БД.

    Живёт в коде приложения, а не в Alembic: `alembic upgrade head` в этом проекте
    не запускается нигде (ни в CI, ни в релизе, ни из Tauri), так что ревизия
    просто никогда бы не выполнилась. Схему это и не меняет — всё внутри JSON.

    Назван по образцу DataDirMigrator (paths.py): та же роль — подобрать
    состояние, оставленное прошлой версией.
    """

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
        # Проход 1 — чистый: нормализуем записи и вынимаем ключи, ничего никуда
        # не записывая. Отделён от прохода 2 намеренно: к моменту, когда
        # начинается ввод-вывод, `entries` приведён к финальному виду целиком.
        # Слитый в один цикл вариант оставлял бы список нормализованным лишь до
        # первой упавшей записи — и любой будущий ранний _write_raw записал бы
        # этот огрызок в колонку, потеряв ключи остальных.
        moved = 0
        try:
            to_move: list[tuple[str, str]] = []  # account -> secret
            for entry in entries:
                entry.setdefault("id", uuid4().hex)
                key = entry.pop("api_key", None)
                entry["has_api_key"] = bool(key) or bool(
                    entry.get("has_api_key", False)
                )
                if key:
                    to_move.append((account_for(str(entry["id"])), str(key)))

            # Проход 2 — ввод-вывод. Колонку не трогаем, пока в хранилище не
            # легли ВСЕ ключи: любой сбой здесь оставляет БД ровно как была, и
            # следующий старт повторит миграцию с нуля.
            for account, secret in to_move:
                await self._store.set(account, secret)
                moved += 1
        except SecretStoreUnavailableError as e:
            # Ожидаемый, ретраимый случай: хранилище — ненадёжная сторона (диск
            # полон, нет прав, связка заблокирована). Колонку не трогаем вовсе:
            # ключ остаётся на месте, следующий старт повторит.
            self._log.warning(
                "Секретное хранилище недоступно, повторим на следующем старте: %s", e
            )
            return
        except Exception as e:
            # НЕ сбой хранилища — баг в самом миграторе (например, битая
            # запись). Колонку всё равно не трогаем, потому что упасть на
            # старте бэкенда хуже, чем повторить попытку — но это не outage,
            # и маскировать его под "хранилище недоступно" нельзя: без
            # различия такая ошибка ретраится на каждом старте бесконечно.
            self._log.error("Неожиданный сбой SecretMigrator'а: %s", e)
            return
        await self._write_raw(entries)
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
        """Сырым SQL мимо LLMDeploymentList: доменная модель про api_key либо уже
        не знает, либо перестанет знать — и молча выбросит ключ, который мы и
        пришли спасать (pydantic v2 игнорирует лишние поля)."""
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
        """UPDATE не стирает плейнтекст с диска: старая страница остаётся в WAL
        и в свободных страницах основного файла. Честная зачистка — чекпойнт с
        усечением WAL плюс VACUUM (в транзакции VACUUM нельзя, поэтому AUTOCOMMIT).

        Предел честности: на SSD освобождённые блоки файловой системы всё ещё
        могут физически хранить данные — гарантировать стирание нельзя.
        """
        async with self._engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
            await conn.exec_driver_sql("VACUUM")
