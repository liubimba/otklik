import asyncio
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from otklik_backend.log import get_logger


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


class X11WindowController:
    def __init__(
        self,
        profile_dir: Path,
        app_window_name: str,
        browser_width: int = 1024,
    ) -> None:
        self._profile_dir = profile_dir
        self._app_window_name = app_window_name
        self._browser_width = browser_width
        self._xdotool = shutil.which("xdotool") or "xdotool"
        self._browser_window_id: str | None = None
        self._log = get_logger(self.__class__.__name__)

    @classmethod
    def available(cls) -> bool:
        return (
            sys.platform.startswith("linux")
            and shutil.which("xdotool") is not None
            and bool(os.environ.get("DISPLAY"))
        )

    async def hide(self) -> None:
        window_id = await self._resolve_browser_window()
        if window_id is None:
            self._log.warning("Cannot hide: browser window not found")
            return
        await self._xdo("windowunmap", window_id)
        self._log.info("Browser window hidden (unmapped)", window_id=window_id)

    async def show_near_app(self) -> None:
        window_id = await self._resolve_browser_window()
        if window_id is None:
            self._log.warning("Cannot show: browser window not found")
            return
        await self._xdo("windowmap", window_id)

        rect = await self._compute_placement()
        if rect is not None:
            await self._xdo("windowsize", window_id, str(rect.width), str(rect.height))
            await self._xdo("windowmove", window_id, str(rect.x), str(rect.y))
        await self._xdo("windowactivate", window_id)
        self._log.info(
            "Browser window shown near app", window_id=window_id, placement=rect
        )

    async def _compute_placement(self) -> Rect | None:
        app = await self._app_geometry()
        screen = await self._screen_size()
        if app is None or screen is None:
            self._log.warning("App/screen geometry unavailable; mapping without move")
            return None
        return BesidePlacement(
            screen_width=screen[0],
            screen_height=screen[1],
            browser_width=self._browser_width,
        ).beside(app)

    async def _resolve_browser_window(self, attempts: int = 5) -> str | None:
        if self._browser_window_id is not None:
            return self._browser_window_id
        for attempt in range(attempts):
            window_id = await self._find_browser_window()
            if window_id is not None:
                self._browser_window_id = window_id
                return window_id
            if attempt < attempts - 1:
                await asyncio.sleep(0.3)
        return None

    async def _find_browser_window(self) -> str | None:
        pid = self._find_browser_pid()
        if pid is None:
            return None
        code, out = await self._xdo("search", "--onlyvisible", "--pid", str(pid))
        if code == 0 and out:
            return await self._largest_window(out.split())
        code, out = await self._xdo("search", "--pid", str(pid))
        if code != 0 or not out:
            return None
        for candidate in out.split():
            _, name = await self._xdo("getwindowname", candidate)
            if name:
                return candidate
        return out.split()[0]

    async def _largest_window(self, candidates: list[str]) -> str | None:
        if not candidates:
            return None
        best: str | None = None
        best_area = -1
        for candidate in candidates:
            geom = await self._window_geometry(candidate)
            area = 0 if geom is None else geom.width * geom.height
            if area > best_area:
                best_area = area
                best = candidate
        return best

    def _find_browser_pid(self) -> int | None:
        needle = f"--user-data-dir={self._profile_dir}"
        for proc in Path("/proc").iterdir():
            if not proc.name.isdigit():
                continue
            try:
                cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ")
            except OSError:
                continue
            text = cmdline.decode(errors="ignore")
            if needle in text and "--type=" not in text:
                return int(proc.name)
        return None

    async def _app_geometry(self) -> Rect | None:
        code, out = await self._xdo("search", "--name", self._app_window_name)
        if code != 0 or not out:
            return None
        return await self._window_geometry(out.split()[0])

    async def _window_geometry(self, window_id: str) -> Rect | None:
        code, geom = await self._xdo("getwindowgeometry", "--shell", window_id)
        if code != 0:
            return None
        values: dict[str, int] = {}
        for line in geom.splitlines():
            key, _, value = line.partition("=")
            if value.strip().lstrip("-").isdigit():
                values[key.strip()] = int(value)
        try:
            return Rect(
                x=values["X"],
                y=values["Y"],
                width=values["WIDTH"],
                height=values["HEIGHT"],
            )
        except KeyError:
            return None

    async def _screen_size(self) -> tuple[int, int] | None:
        code, out = await self._xdo("getdisplaygeometry")
        if code != 0:
            return None
        parts = out.split()
        if len(parts) != 2:
            return None
        return int(parts[0]), int(parts[1])

    async def _xdo(self, *args: str) -> tuple[int, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                self._xdotool,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            self._log.error("Failed to invoke xdotool", args=args, error=str(exc))
            return 1, ""
        stdout, stderr = await proc.communicate()
        code = proc.returncode or 0
        if code != 0:
            self._log.warning(
                "xdotool returned non-zero",
                args=args,
                code=code,
                stderr=stderr.decode(errors="ignore").strip(),
            )
        return code, stdout.decode(errors="ignore").strip()
