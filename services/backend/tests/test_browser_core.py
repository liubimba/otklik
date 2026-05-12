import sys
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="Headful Chromium currently set up only on Linux(xvfb)",
)


async def test_browser_core(tmp_path):
    from headhunter_backend.browser import BrowserCore

    browser_core = BrowserCore(profile_dir=tmp_path / "test-profile")
    await browser_core.start()
    await browser_core.stop()
