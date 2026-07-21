from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from otklik_backend.log import get_logger

CDPSessionProvider = Callable[[], Awaitable[Any]]

OFF_SCREEN_LIMIT = -10000
RESCUE_ORIGIN = {"left": 80, "top": 80}


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


class BesidePlacement:
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        browser_width: int = 1024,
        gap: int = 12,
    ) -> None:
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._browser_width = browser_width
        self._gap = gap

    def beside(self, app: Rect) -> Rect:
        width = min(self._browser_width, self._screen_width)
        height = min(app.height, self._screen_height)

        x = app.x + app.width + self._gap
        if x + width > self._screen_width:
            x = app.x + (app.width - width) // 2

        x = max(0, min(x, self._screen_width - width))
        y = max(0, min(app.y, self._screen_height - height))
        return Rect(x=x, y=y, width=width, height=height)


@runtime_checkable
class WindowController(Protocol):
    async def hide(self) -> None: ...

    async def show_near_app(self) -> None: ...


class NoopWindowController:
    def __init__(self) -> None:
        self._log = get_logger(self.__class__.__name__)

    async def hide(self) -> None:
        self._log.info("Window control unavailable; leaving browser window as-is")

    async def show_near_app(self) -> None:
        self._log.info("Window control unavailable; leaving browser window as-is")


class CDPWindowController:
    def __init__(self, session_provider: CDPSessionProvider) -> None:
        self._session_provider = session_provider
        self._log = get_logger(self.__class__.__name__)

    async def hide(self) -> None:
        await self._set_window_state("minimized")

    async def show_near_app(self) -> None:
        await self._set_window_state("normal", rescue_off_screen=True)

    async def _set_window_state(
        self, state: str, rescue_off_screen: bool = False
    ) -> None:
        try:
            session = await self._session_provider()
            if session is None:
                self._log.warning("Cannot control browser window: no CDP session")
                return
            info = await session.send("Browser.getWindowForTarget")
            window_id = info["windowId"]
            await session.send(
                "Browser.setWindowBounds",
                {"windowId": window_id, "bounds": {"windowState": state}},
            )
            self._log.info("Browser window state set", window_state=state)
            if rescue_off_screen and self._is_off_screen(info.get("bounds")):
                await session.send(
                    "Browser.setWindowBounds",
                    {"windowId": window_id, "bounds": dict(RESCUE_ORIGIN)},
                )
                self._log.info("Browser window pulled back onto the screen")
        except Exception as exc:
            self._log.warning(
                "Failed to set browser window state via CDP",
                window_state=state,
                error=str(exc),
            )

    def _is_off_screen(self, bounds: Any) -> bool:
        if not isinstance(bounds, dict):
            return False
        return any(
            isinstance(bounds.get(edge), int) and bounds[edge] <= OFF_SCREEN_LIMIT
            for edge in ("left", "top")
        )
