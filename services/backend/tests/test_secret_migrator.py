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
from otklik_backend.secrets.store import (
    SecretStore,
    SecretStorageMode,
    SecretStoreUnavailableError,
    account_for,
)
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


class _PartiallyBrokenSecretStore:
    """set() успевает для первого аккаунта и падает на втором — хранилище
    недоступно. Проверяет, что миграция не пишет колонку частично: либо все
    ключи перенесены и колонка вычищена, либо ни один и колонка нетронута."""

    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    @property
    def mode(self) -> SecretStorageMode:
        return SecretStorageMode.FILE

    async def get(self, account: str) -> str | None:
        return self.items.get(account)

    async def set(self, account: str, secret: str) -> None:
        if self.items:
            raise SecretStoreUnavailableError()
        self.items[account] = secret

    async def delete(self, account: str) -> None:
        pass


async def test_multi_deployment_failure_keeps_every_key_in_the_column(
    test_database: DbHandle,
) -> None:
    """Атомарность на несколько записей: первая ушла в store, вторая упала —
    ни один ключ не должен пропасть из колонки (никакой частичной зачистки).

    Раньше тест требовал колонку байт-в-байт исходной. Это оказалось слишком
    сильным требованием: проштамповать id НУЖНО до переноса ключей, иначе
    упавший проход терял бы id вместе с памятью и следующий старт копил бы
    сирот в связке (см. test_failed_store_write_persists_ids_so_the_retry_
    reuses_the_account). Инвариант, который здесь на самом деле защищается, —
    не «колонка не изменилась», а «ключ не потерян»."""
    entries = [
        {"model": "gigachat/GigaChat-2", "api_key": LEGACY_KEY, "api_base": None},
        {
            "model": "openai/gpt-4o",
            "api_key": "sk-second-must-not-vanish",
            "api_base": None,
        },
    ]
    await _seed_legacy_row(test_database.session_maker, entries)

    store: SecretStore = _PartiallyBrokenSecretStore()
    migrator = SecretMigrator(
        session_maker=test_database.session_maker,
        engine=test_database.engine,
        store=store,
    )
    await migrator.migrate()

    column = json.loads(await _raw_column(test_database.session_maker))
    # Оба ключа на месте: тот, что успел уехать в store, — тоже (дубликат
    # безвреден, зачистка будет только когда доедут все).
    assert column[0]["api_key"] == LEGACY_KEY
    assert column[1]["api_key"] == "sk-second-must-not-vanish"


async def test_failed_store_write_persists_ids_so_the_retry_reuses_the_account(
    test_database: DbHandle, fake_secret_store: FakeSecretStore
) -> None:
    """Сбой хранилища не должен плодить сирот в связке.

    id — это имя аккаунта. Если штамповать его только в памяти, упавший проход
    терял бы id вместе с ней: следующий старт сминтил бы новый uuid, положил
    ключ под новым аккаунтом, а запись под старым осталась бы в связке
    навсегда — по сироте за каждую неудачную загрузку. Поэтому id уезжает в
    колонку ДО переноса ключей, и повтор пишет в тот же аккаунт."""
    await _seed_legacy_row(
        test_database.session_maker,
        [{"model": "gigachat/GigaChat-2", "api_key": LEGACY_KEY, "api_base": None}],
    )

    # Первый старт: хранилище недоступно.
    await SecretMigrator(
        session_maker=test_database.session_maker,
        engine=test_database.engine,
        store=_BrokenSecretStore(),  # type: ignore[arg-type]
    ).migrate()

    after_failure = json.loads(await _raw_column(test_database.session_maker))
    # Ключ никуда не делся — терять его нельзя.
    assert after_failure[0]["api_key"] == LEGACY_KEY
    # ...но id уже проштампован и переживёт перезапуск.
    stamped_id = after_failure[0]["id"]
    assert len(stamped_id) == 32

    # Второй старт: хранилище починилось.
    await SecretMigrator(
        session_maker=test_database.session_maker,
        engine=test_database.engine,
        store=fake_secret_store,
    ).migrate()

    after_retry = json.loads(await _raw_column(test_database.session_maker))
    assert after_retry[0]["id"] == stamped_id  # тот же id, а не новый uuid
    assert "api_key" not in after_retry[0]
    # Ровно один аккаунт — сирот нет.
    assert fake_secret_store.items == {account_for(stamped_id): LEGACY_KEY}
