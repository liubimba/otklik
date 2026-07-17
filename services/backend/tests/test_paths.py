from pathlib import Path

from otklik_backend.paths import AppPaths, DataDirMigrator


class TestAppPaths:
    def test_layout_hangs_off_the_app_dir(self, tmp_path: Path) -> None:
        paths = AppPaths(home=tmp_path)

        assert paths.root == tmp_path / ".otklik"
        assert paths.db_file == tmp_path / ".otklik" / "db.sqlite"
        assert paths.browser_profile == tmp_path / ".otklik" / "chrome-profile"

    def test_legacy_roots_point_at_the_pre_rename_dir(self, tmp_path: Path) -> None:
        paths = AppPaths(home=tmp_path)

        assert paths.legacy_roots == (tmp_path / ".headhunter_ai",)


class TestDataDirMigrator:
    def _migrator(self, home: Path) -> DataDirMigrator:
        return DataDirMigrator(paths=AppPaths(home=home))

    def test_no_legacy_dir_is_a_no_op(self, tmp_path: Path) -> None:
        moved = self._migrator(home=tmp_path).migrate()

        assert moved == []
        assert not (tmp_path / ".otklik").exists()

    def test_adopts_database_and_browser_profile(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".headhunter_ai"
        (legacy / "chrome-profile").mkdir(parents=True)
        (legacy / "chrome-profile" / "Cookies").write_text("session")
        (legacy / "db.sqlite").write_text("sqlite")

        moved = self._migrator(home=tmp_path).migrate()

        root = tmp_path / ".otklik"
        assert (root / "db.sqlite").read_text() == "sqlite"
        assert (root / "chrome-profile" / "Cookies").read_text() == "session"
        assert sorted(moved) == [root / "chrome-profile", root / "db.sqlite"]
        assert not legacy.exists()

    def test_merges_into_a_dir_the_ui_already_created(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".headhunter_ai"
        legacy.mkdir()
        (legacy / "db.sqlite").write_text("sqlite")
        root = tmp_path / ".otklik"
        root.mkdir()
        (root / "consent.json").write_text("{}")

        moved = self._migrator(home=tmp_path).migrate()

        assert moved == [root / "db.sqlite"]
        assert (root / "db.sqlite").read_text() == "sqlite"
        assert (root / "consent.json").read_text() == "{}"
        assert not legacy.exists()

    def test_existing_entry_wins_and_its_legacy_copy_survives(
        self, tmp_path: Path
    ) -> None:
        legacy = tmp_path / ".headhunter_ai"
        legacy.mkdir()
        (legacy / "db.sqlite").write_text("stale")
        root = tmp_path / ".otklik"
        root.mkdir()
        (root / "db.sqlite").write_text("current")

        moved = self._migrator(home=tmp_path).migrate()

        assert moved == []
        assert (root / "db.sqlite").read_text() == "current"
        assert (legacy / "db.sqlite").read_text() == "stale"

    def test_is_idempotent(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".headhunter_ai"
        legacy.mkdir()
        (legacy / "db.sqlite").write_text("sqlite")

        migrator = self._migrator(home=tmp_path)
        first = migrator.migrate()
        second = migrator.migrate()

        assert len(first) == 1
        assert second == []
        assert (tmp_path / ".otklik" / "db.sqlite").read_text() == "sqlite"
