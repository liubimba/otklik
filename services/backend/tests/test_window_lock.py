from pathlib import Path
from typing import Any

from otklik_backend.browser import BrowserCore
from otklik_backend.browser.guard import SinglePageGuard
from otklik_backend.orchestrator.search.filter_session import FilterSession


class FakeRawPage:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


async def test_core_closes_a_tab_opened_in_the_locked_window(tmp_path: Path) -> None:
    core = BrowserCore(profile_dir=tmp_path)
    locked = FakeRawPage()
    guard = SinglePageGuard("hh.ru")
    guard.lock(locked)  # type: ignore[arg-type]
    core._guard = guard

    foreign = FakeRawPage()
    core._on_new_page(foreign)  # type: ignore[arg-type]
    await core.drain_guard_tasks()

    assert foreign.closed is True


async def test_core_leaves_the_locked_page_alone(tmp_path: Path) -> None:
    core = BrowserCore(profile_dir=tmp_path)
    locked = FakeRawPage()
    guard = SinglePageGuard("hh.ru")
    guard.lock(locked)  # type: ignore[arg-type]
    core._guard = guard

    core._on_new_page(locked)  # type: ignore[arg-type]
    await core.drain_guard_tasks()

    assert locked.closed is False


class RecordingCore:
    def __init__(self) -> None:
        self.locked_host: str | None = None
        self.unlocked = 0
        self.page = FakeBrowserPage()

    async def new_page(self, url: str) -> "FakeBrowserPage":
        return self.page

    async def lock_window(self, page: Any, allowed_host: str) -> None:
        self.locked_host = allowed_host

    async def unlock_window(self) -> None:
        self.unlocked += 1


class FakeBrowserPage:
    def __init__(self) -> None:
        self._url = "https://hh.ru/search/vacancy"
        self.closed = False

    def get_url(self) -> str:
        return self._url

    def is_closed(self) -> bool:
        return self.closed

    async def close(self) -> None:
        self.closed = True


async def test_filter_session_locks_the_window_to_hh_ru() -> None:
    core = RecordingCore()

    await FilterSession.execute(core=core)  # type: ignore[arg-type]

    assert core.locked_host == "hh.ru"


async def test_confirm_unlocks_the_window() -> None:
    core = RecordingCore()
    session = await FilterSession.execute(core=core)  # type: ignore[arg-type]

    await session.confirm()

    assert core.unlocked == 1


async def test_cancel_unlocks_the_window() -> None:
    core = RecordingCore()
    session = await FilterSession.execute(core=core)  # type: ignore[arg-type]

    await session.cancel()

    assert core.unlocked == 1
