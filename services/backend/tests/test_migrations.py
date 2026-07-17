from pathlib import Path

from sqlalchemy import create_engine, inspect

from otklik_backend.db.migrations import SchemaMigrator, alembic_root


def test_alembic_root_contains_the_versions_directory() -> None:
    assert (alembic_root() / "versions").is_dir()


def _tables_of(db: Path) -> set[str]:
    return set(inspect(create_engine(f"sqlite:///{db}")).get_table_names())


def test_upgrade_creates_the_schema_on_an_empty_database(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    SchemaMigrator(database_url=f"sqlite+aiosqlite:///{db}").upgrade_to_head()
    assert {"settings", "vacancies", "applications"} <= _tables_of(db)


def test_upgrade_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    migrator = SchemaMigrator(database_url=f"sqlite+aiosqlite:///{db}")
    migrator.upgrade_to_head()
    migrator.upgrade_to_head()
    assert "settings" in _tables_of(db)


def test_upgrade_stamps_the_alembic_version_table(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    SchemaMigrator(database_url=f"sqlite+aiosqlite:///{db}").upgrade_to_head()
    assert "alembic_version" in _tables_of(db)


def test_upgrade_migrates_the_given_url_and_not_the_app_database(
    tmp_path: Path,
) -> None:
    db = tmp_path / "db.sqlite"
    SchemaMigrator(database_url=f"sqlite+aiosqlite:///{db}").upgrade_to_head()
    assert db.exists()
    assert "settings" in _tables_of(db)
