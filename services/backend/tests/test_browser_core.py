import sys

import pytest

from headhunter_backend.api.schemas import AuthStatusAPISchema
from headhunter_backend.browser import BrowserCore
from headhunter_backend.sites.hh_ru.auth_flow import HHRUAuthFlow

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="Headful Chromium currently set up only on Linux(xvfb)",
)


async def test_browser_core(tmp_path):
    browser_core = BrowserCore(profile_dir=tmp_path / "test-profile")
    await browser_core.start()
    await browser_core.stop()


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
