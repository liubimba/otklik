import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from otklik_backend.log import get_logger


def alembic_root() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled is not None:
        return Path(bundled) / "alembic"
    return Path(__file__).resolve().parents[3] / "alembic"


class SchemaMigrator:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._log = get_logger(self.__class__.__name__)

    def upgrade_to_head(self) -> None:
        config = Config()
        config.set_main_option("script_location", str(alembic_root()))
        config.set_main_option("sqlalchemy.url", self._database_url)
        self._log.info("Upgrading database schema to head")
        command.upgrade(config, "head")
