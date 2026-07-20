from pathlib import Path
from typing import Any

from otklik_backend.browser import BrowserCore
from otklik_backend.browser.window import CDPWindowController


class FakeCDPSession:
    def __init__(self, window_id: int = 7) -> None:
        self._window_id = window_id
        self.sent: list[tuple[str, dict[str, Any]]] = []

    async def send(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self.sent.append((method, params or {}))
        if method == "Browser.getWindowForTarget":
            return {"windowId": self._window_id, "bounds": {}}
        return {}


def _provider(session: Any):
    async def provide() -> Any:
        return session

    return provide


async def test_hide_minimizes_the_browser_window_through_cdp() -> None:
    session = FakeCDPSession(window_id=7)
    controller = CDPWindowController(_provider(session))

    await controller.hide()

    assert (
        "Browser.setWindowBounds",
        {"windowId": 7, "bounds": {"windowState": "minimized"}},
    ) in session.sent


async def test_show_restores_the_browser_window_through_cdp() -> None:
    session = FakeCDPSession(window_id=7)
    controller = CDPWindowController(_provider(session))

    await controller.show_near_app()

    assert (
        "Browser.setWindowBounds",
        {"windowId": 7, "bounds": {"windowState": "normal"}},
    ) in session.sent


async def test_controller_is_a_noop_when_no_cdp_session_is_available() -> None:
    controller = CDPWindowController(_provider(None))

    await controller.hide()
    await controller.show_near_app()


async def test_controller_swallows_cdp_errors_and_never_raises() -> None:
    class ExplodingSession:
        async def send(self, method: str, params: dict[str, Any] | None = None) -> Any:
            raise RuntimeError("target closed")

    controller = CDPWindowController(_provider(ExplodingSession()))

    await controller.hide()
    await controller.show_near_app()


def test_browser_core_hides_the_browser_through_cdp_not_xdotool(tmp_path: Path) -> None:
    core = BrowserCore(profile_dir=tmp_path)

    assert isinstance(core._window, CDPWindowController)
