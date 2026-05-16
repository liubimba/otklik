import sys
from headhunter_backend.api.schemas import AuthStatus
from headhunter_backend.browser import BrowserCore
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="Headful Chromium currently set up only on Linux(xvfb)",
)


async def test_browser_core(tmp_path):
    browser_core = BrowserCore(profile_dir=tmp_path / "test-profile")
    await browser_core.start()
    await browser_core.stop()


async def test_browser_core_authentication(tmp_path):
    browser_core: BrowserCore = BrowserCore(profile_dir=tmp_path / "test-profile")
    await browser_core.start()
    try:
        status: AuthStatus = await browser_core.get_auth_status()
        assert (
            not status.is_authorized()
        ), "Expected user to not be authenticated initially"
        await browser_core._context.add_cookies(
            [{"name": "hhrole", "value": "applicant", "domain": ".hh.ru", "path": "/"}]
        )
        await browser_core.wait_for_login(
            poll_interval=0.1
        )  # This will set the auth status to authorized
        status = await browser_core.get_auth_status()
        assert (
            status.is_authorized()
        ), "Expected user to be authenticated after setting cookie"
    finally:
        await browser_core.stop()
