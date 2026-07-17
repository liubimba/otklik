import shutil
from pathlib import Path

from otklik_backend.log import get_logger

APP_DIR_NAME = ".otklik"

LEGACY_APP_DIR_NAMES = (".headhunter_ai",)


class AppPaths:
    def __init__(self, home: Path | None = None) -> None:
        self._home = Path.home() if home is None else home

    @property
    def root(self) -> Path:
        return self._home / APP_DIR_NAME

    @property
    def db_file(self) -> Path:
        return self.root / "db.sqlite"

    @property
    def browser_profile(self) -> Path:
        return self.root / "chrome-profile"

    @property
    def legacy_roots(self) -> tuple[Path, ...]:
        return tuple(self._home / name for name in LEGACY_APP_DIR_NAMES)


class DataDirMigrator:
    def __init__(self, paths: AppPaths | None = None) -> None:
        self._paths = AppPaths() if paths is None else paths
        self.logger = get_logger(self.__class__.__name__)

    def migrate(self) -> list[Path]:
        moved: list[Path] = []
        for legacy in self._paths.legacy_roots:
            if legacy.is_dir():
                moved.extend(self._adopt(legacy=legacy))
        return moved

    def _adopt(self, legacy: Path) -> list[Path]:
        target = self._paths.root
        target.mkdir(parents=True, exist_ok=True)

        moved: list[Path] = []
        for entry in sorted(legacy.iterdir()):
            destination = target / entry.name
            if destination.exists():
                self.logger.warning(
                    "Keeping the current entry, leaving the legacy one behind",
                    entry=entry.name,
                    legacy=str(legacy),
                )
                continue
            shutil.move(str(entry), str(destination))
            moved.append(destination)

        if not any(legacy.iterdir()):
            legacy.rmdir()

        self.logger.info(
            "Adopted legacy data directory",
            legacy=str(legacy),
            target=str(target),
            moved=len(moved),
        )
        return moved
