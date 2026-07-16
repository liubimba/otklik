"""SecretMigrator переносит легаси-ключи из открытой JSON-колонки в хранилище
и вычищает их из БД. Живёт в коде приложения, не в Alembic: `alembic upgrade
head` в этом проекте не запускается нигде.

test_scrubbed_key_is_gone_from_the_database_file — главный тест задачи: UPDATE
колонки не стирает плейнтекст с диска (WAL, свободные страницы). Без
wal_checkpoint(TRUNCATE) + VACUUM ключ находится обычным grep по файлу."""

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.secrets.migrator import SecretMigrator
from otklik_backend.secrets.store import SecretStore, SecretStorageMode, account_for
from tests.conftest import FakeSecretStore, DbHandle

LEGACY_KEY = "sk-legacy-must-not-survive"


async def _seed_legacy_row(
    session_maker: async_sessionmaker[AsyncSession], entries: list[dict]
) -> None:
    """Пишем строку настроек сырым SQL: фикстура test_database даёт пустую БД."""
    async with session_maker() as session:
        await session.execute(
            text(
                "INSERT INTO settings (id, letter_style, resume_text, max_pages,"
                " max_vacancies, daily_limit, hourly_limit, min_delay_ms,"
                " delay_jitter_ms, auto_submit, llm_deployments, llm_system_prompt)"
                " VALUES (1, '', '', 5, 50, 30, 5, 800, 400, 0, :deployments, NULL)"
            ),
            {"deployments": json.dumps(entries)},
        )
        await session.commit()


async def _raw_column(session_maker: async_sessionmaker[AsyncSession]) -> str:
    async with session_maker() as session:
        result = await session.execute(
            text("SELECT llm_deployments FROM settings WHERE id = 1")
        )
        return str(result.scalar_one())


class _BrokenSecretStore:
    """Хранилище, у которого set() всегда падает: диск полон, прав нет —
    неважно что именно, важно что ключ должен остаться на месте."""

    @property
    def mode(self) -> SecretStorageMode:
        return SecretStorageMode.FILE

    async def get(self, account: str) -> str | None:
        return None

    async def set(self, account: str, secret: str) -> None:
        raise OSError("disk full")

    async def delete(self, account: str) -> None:
        pass


async def test_migrates_legacy_key_into_the_store(
    test_database: DbHandle, fake_secret_store: FakeSecretStore
) -> None:
    await _seed_legacy_row(
        test_database.session_maker,
        [{"model": "gigachat/GigaChat-2", "api_key": LEGACY_KEY, "api_base": None}],
    )
    migrator = SecretMigrator(
        session_maker=test_database.session_maker,
        engine=test_database.engine,
        store=fake_secret_store,
    )
    await migrator.migrate()

    column = json.loads(await _raw_column(test_database.session_maker))
    assert "api_key" not in column[0]
    assert column[0]["has_api_key"] is True
    assert len(column[0]["id"]) == 32
    assert fake_secret_store.items[account_for(column[0]["id"])] == LEGACY_KEY


async def test_scrubbed_key_is_gone_from_the_database_file(
    test_database: DbHandle, fake_secret_store: FakeSecretStore
) -> None:
    """ГЛАВНЫЙ тест задачи: затереть колонку мало — WAL и свободные страницы
    хранят старый плейнтекст. Падает без wal_checkpoint(TRUNCATE) + VACUUM."""
    await _seed_legacy_row(
        test_database.session_maker,
        [{"model": "gigachat/GigaChat-2", "api_key": LEGACY_KEY, "api_base": None}],
    )
    migrator = SecretMigrator(
        session_maker=test_database.session_maker,
        engine=test_database.engine,
        store=fake_secret_store,
    )
    await migrator.migrate()

    db_file: Path = test_database.db_path
    assert LEGACY_KEY.encode() not in db_file.read_bytes()
    wal = db_file.with_name(db_file.name + "-wal")
    if wal.exists():
        assert LEGACY_KEY.encode() not in wal.read_bytes()


async def test_is_idempotent(
    test_database: DbHandle, fake_secret_store: FakeSecretStore
) -> None:
    await _seed_legacy_row(
        test_database.session_maker,
        [{"model": "gigachat/GigaChat-2", "api_key": LEGACY_KEY, "api_base": None}],
    )
    migrator = SecretMigrator(
        session_maker=test_database.session_maker,
        engine=test_database.engine,
        store=fake_secret_store,
    )
    await migrator.migrate()
    first = json.loads(await _raw_column(test_database.session_maker))
    await migrator.migrate()
    second = json.loads(await _raw_column(test_database.session_maker))
    assert first == second  # id не перештамповался, ключ не тронут
    assert fake_secret_store.items[account_for(first[0]["id"])] == LEGACY_KEY


async def test_stamps_id_and_flag_for_a_keyless_row(
    test_database: DbHandle, fake_secret_store: FakeSecretStore
) -> None:
    """Локальная модель без ключа: id проштамповать надо, в хранилище — ничего."""
    await _seed_legacy_row(
        test_database.session_maker,
        [{"model": "ollama_chat/qwen2.5:7b", "api_base": "http://localhost:11434"}],
    )
    migrator = SecretMigrator(
        session_maker=test_database.session_maker,
        engine=test_database.engine,
        store=fake_secret_store,
    )
    await migrator.migrate()

    column = json.loads(await _raw_column(test_database.session_maker))
    assert len(column[0]["id"]) == 32
    assert column[0]["has_api_key"] is False
    assert fake_secret_store.items == {}


async def test_store_failure_leaves_the_column_untouched(
    test_database: DbHandle,
) -> None:
    """Хранилище упало (нет места/прав) — ключ НЕ теряем, ретраим на следующем старте."""
    await _seed_legacy_row(
        test_database.session_maker,
        [{"model": "gigachat/GigaChat-2", "api_key": LEGACY_KEY, "api_base": None}],
    )
    store: SecretStore = _BrokenSecretStore()
    migrator = SecretMigrator(
        session_maker=test_database.session_maker,
        engine=test_database.engine,
        store=store,
    )
    await migrator.migrate()

    column = json.loads(await _raw_column(test_database.session_maker))
    assert column[0]["api_key"] == LEGACY_KEY
