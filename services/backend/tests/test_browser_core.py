import sys

import pytest
from patchright.async_api import Error as PlaywrightError

from headhunter_backend.api.schemas import AuthStatusAPISchema
from headhunter_backend.browser import BrowserCore
from headhunter_backend.browser import core as core_module
from headhunter_backend.browser.exceptions import BrowserNetworkError
from headhunter_backend.browser.window import NoopWindowController
from headhunter_backend.sites.hh_ru.auth_flow import HHRUAuthFlow

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
    """HHRUAuthFlow wraps a BrowserCore and reads the `hhrole` cookie to decide
    authentication. This test drives it end-to-end against a real Chromium."""
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


# ─ new_page() retry policy ───────────────────────────────────────────
#
# `new_page` promises MAX_ATTEMPTS tries against transient Chromium network
# failures (net::ERR_NETWORK_CHANGED and friends). These tests drive that
# promise against a fake BrowserContext — no real Chromium involved.


class FakePage:
    """Stands in for a patchright Page: `goto` fails as scripted, then works."""

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
    """Hands out a fresh FakePage per new_page() call, each with its own verdict
    taken from `failures` — index N is what the Nth attempt's goto() raises."""

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
    """A single ERR_NETWORK_CHANGED must not kill the navigation — the second
    attempt succeeds and the caller gets a live page."""
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
    """Only Playwright `Error`s are transient. Anything else is a real bug and
    must surface unchanged instead of being retried and masked."""
    context = FakeContext([ValueError("boom")])
    core._context = context  # type: ignore[assignment]

    with pytest.raises(ValueError):
        await core.new_page(url="https://hh.ru/search/vacancy")

    assert len(context.pages) == 1
