import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from patchright.async_api import Error as PlaywrightError

from otklik_backend.api.schemas import AuthStatusAPISchema
from otklik_backend.browser import BrowserCore
from otklik_backend.browser import core as core_module
from otklik_backend.browser.exceptions import BrowserNetworkError
from otklik_backend.browser.window import NoopWindowController
from otklik_backend.sites.hh_ru.auth_flow import HHRUAuthFlow

requires_chromium = pytest.mark.skipif(
    sys.platform != "linux",
    reason="Headful Chromium currently set up only on Linux(xvfb)",
)


@requires_chromium
async def test_browser_core(tmp_path):
    browser_core = BrowserCore(profile_dir=tmp_path / "test-profile")
    await browser_core.start()
    await browser_core.stop()


@requires_chromium
async def test_hhru_auth_flow(tmp_path):
    browser_core: BrowserCore = BrowserCore(profile_dir=tmp_path / "test-profile")
    await browser_core.start()
    auth_flow = HHRUAuthFlow(browser=browser_core)
    try:
        status: AuthStatusAPISchema = await auth_flow.get_auth_status()
        assert (
            not status.is_authorized()
        ), "Expected user to not be authenticated initially"
        await browser_core._context.add_cookies(
            [{"name": "hhrole", "value": "applicant", "domain": ".hh.ru", "path": "/"}]
        )
        await auth_flow.wait_for_login(poll_interval=0.1)
        status = await auth_flow.get_auth_status()
        assert (
            status.is_authorized()
        ), "Expected user to be authenticated after setting cookie"
    finally:
        await browser_core.stop()


class FakePage:
    def __init__(self, failures: list[Exception | None]) -> None:
        self._failures = failures
        self.closed = False
        self.goto_calls = 0

    async def goto(self, url: str) -> None:
        idx = self.goto_calls
        self.goto_calls += 1
        failure = self._failures[idx] if idx < len(self._failures) else None
        if failure is not None:
            raise failure

    async def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, failures: list[Exception | None]) -> None:
        self._failures = failures
        self.pages: list[FakePage] = []

    async def new_page(self) -> FakePage:
        idx = len(self.pages)
        failure = self._failures[idx] if idx < len(self._failures) else None
        page = FakePage([failure])
        self.pages.append(page)
        return page


def _network_error() -> PlaywrightError:
    return PlaywrightError(
        "Page.goto: net::ERR_NETWORK_CHANGED at https://novosibirsk.hh.ru/search/vacancy"
    )


@pytest.fixture
def core(tmp_path, monkeypatch) -> BrowserCore:
    monkeypatch.setattr(core_module, "RETRY_DELAY", 0)
    return BrowserCore(profile_dir=tmp_path, window=NoopWindowController())


async def test_new_page_retries_after_a_transient_network_error(core) -> None:
    context = FakeContext([_network_error(), None])
    core._context = context  # type: ignore[assignment]

    page = await core.new_page(url="https://hh.ru/search/vacancy")

    assert page is not None
    assert len(context.pages) == 2, "expected a retry after the transient failure"
    assert context.pages[0].closed, "the failed attempt's page must be closed"


async def test_new_page_gives_up_after_max_attempts(core) -> None:
    context = FakeContext([_network_error()] * core_module.MAX_ATTEMPTS)
    core._context = context  # type: ignore[assignment]

    with pytest.raises(BrowserNetworkError):
        await core.new_page(url="https://hh.ru/search/vacancy")

    assert len(context.pages) == core_module.MAX_ATTEMPTS
    assert all(page.closed for page in context.pages)


async def test_new_page_does_not_retry_non_playwright_errors(core) -> None:
    context = FakeContext([ValueError("boom")])
    core._context = context  # type: ignore[assignment]

    with pytest.raises(ValueError):
        await core.new_page(url="https://hh.ru/search/vacancy")

    assert len(context.pages) == 1


async def test_ensure_started_launches_once_even_when_called_concurrently() -> None:
    core = BrowserCore(profile_dir=Path("/tmp/unused"), window=NoopWindowController())
    starts = 0

    async def fake_start() -> None:
        nonlocal starts
        starts += 1
        await asyncio.sleep(0.01)
        core._context = object()  # type: ignore[assignment]

    with patch.object(core, "start", fake_start):
        await asyncio.gather(*(core.ensure_started() for _ in range(5)))

    assert starts == 1


async def test_ensure_started_retries_after_a_failed_launch() -> None:
    core = BrowserCore(profile_dir=Path("/tmp/unused"), window=NoopWindowController())
    attempts = 0

    async def flaky_start() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("Executable doesn't exist at chrome")
        core._context = object()  # type: ignore[assignment]

    with patch.object(core, "start", flaky_start):
        with pytest.raises(RuntimeError):
            await core.ensure_started()
        await core.ensure_started()

    assert attempts == 2
