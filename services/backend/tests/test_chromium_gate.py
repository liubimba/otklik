from pathlib import Path

from otklik_backend.browser.chromium_gate import ChromiumGate


def test_reports_missing_when_the_directory_does_not_exist(tmp_path: Path) -> None:
    assert ChromiumGate(browsers_dir=tmp_path / "nope").is_installed() is False


def test_reports_missing_when_the_directory_is_empty(tmp_path: Path) -> None:
    assert ChromiumGate(browsers_dir=tmp_path).is_installed() is False


def test_reports_installed_when_a_chromium_directory_exists(tmp_path: Path) -> None:
    (tmp_path / "chromium-1223").mkdir()
    assert ChromiumGate(browsers_dir=tmp_path).is_installed() is True


def test_headless_shell_alone_does_not_count_as_installed(tmp_path: Path) -> None:
    (tmp_path / "chromium_headless_shell-1223").mkdir()
    assert ChromiumGate(browsers_dir=tmp_path).is_installed() is False


def test_exports_the_browsers_path_for_the_patchright_driver(tmp_path: Path) -> None:
    env = ChromiumGate(browsers_dir=tmp_path).driver_env()
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path)
