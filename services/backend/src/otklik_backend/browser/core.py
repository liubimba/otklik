import asyncio
from pathlib import Path

from patchright.async_api import (
    BrowserContext,
    CDPSession,
    Cookie,
    Error,
    Page,
    Playwright,
    async_playwright,
)

from otklik_backend.browser.exceptions import BrowserNetworkError
from otklik_backend.browser.guard import SinglePageGuard
from otklik_backend.browser.page import BrowserPage
from otklik_backend.browser.window import (
    CDPWindowController,
    WindowController,
)
from otklik_backend.log import get_logger
from otklik_backend.paths import AppPaths

MAX_ATTEMPTS = 3
RETRY_DELAY = 1
TAB_POOL_SIZE = 15

CHROMIUM_ARGS = [
    "--ozone-platform=x11",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-background-timer-throttling",
]


class BrowserCore:
    def __init__(
        self,
        profile_dir: Path | None = None,
        window: WindowController | None = None,
    ) -> None:
        self.logger = get_logger(self.__class__.__name__)
        if profile_dir is None:
            self.logger.info("No profile directory provided, using default")
            profile_dir = AppPaths().browser_profile
        self.profile_dir = profile_dir
        self.headless = False
        self._context: BrowserContext | None = None
        self._playwright: Playwright | None = None
        self._cdp: CDPSession | None = None
        self._guard: SinglePageGuard | None = None
        self._guard_tasks: set[asyncio.Task[None]] = set()
        self._reusable_pages: dict[str, BrowserPage] = {}
        self._pool_available: list[BrowserPage] = []
        self._pool_lock = asyncio.Lock()
        self._start_lock = asyncio.Lock()
        self._window = window or CDPWindowController(self._open_cdp_session)

    async def ensure_started(self) -> None:
        if self._context is not None:
            return
        async with self._start_lock:
            if self._context is not None:
                return
            await self.start()

    async def start(self) -> None:
        self.logger.info(
            "Starting browser with profile directory: ",
            profile_dir=str(self.profile_dir),
        )
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            no_viewport=True,
            args=CHROMIUM_ARGS,
        )
        self._context.on("close", self._on_context_closed)
        self._context.on("page", self._on_new_page)
        await self._window.hide()
        await self._prewarm_pool()

    def _on_context_closed(self, *_: object) -> None:
        self.logger.info("Browser context closed")
        self._context = None
        self._cdp = None
        self._guard = None
        self._reusable_pages.clear()
        self._pool_available.clear()

    async def _prewarm_pool(self) -> None:
        if self._context is None:
            return
        for _ in range(TAB_POOL_SIZE):
            try:
                raw = await self._context.new_page()
            except Error as exc:
                self.logger.warning("Failed to prewarm a browser tab", error=str(exc))
                break
            self._pool_available.append(BrowserPage(raw))
        self.logger.info("Prewarmed browser tab pool", size=len(self._pool_available))

    async def acquire(self) -> BrowserPage:
        await self.ensure_started()
        if self._context is None:
            raise RuntimeError("BrowserCore is not started")
        async with self._pool_lock:
            while self._pool_available:
                page = self._pool_available.pop()
                if not page.is_closed():
                    return page
        self.logger.info("Tab pool exhausted, opening an extra tab")
        raw = await self._context.new_page()
        return BrowserPage(raw)

    async def release(self, page: BrowserPage) -> None:
        if page.is_closed():
            return
        async with self._pool_lock:
            if page not in self._pool_available:
                self._pool_available.append(page)

    async def lease_page(self, url: str) -> BrowserPage:
        page = await self.acquire()
        try:
            await self._navigate_with_retry(page, url)
        except Exception:
            await self.release(page)
            raise
        return page

    async def open_reusable_page(self, key: str, url: str) -> BrowserPage:
        existing = self._reusable_pages.get(key)
        if existing is not None and not existing.is_closed():
            await self._navigate_with_retry(existing, url)
            return existing
        page = await self.acquire()
        self._reusable_pages[key] = page
        await self._navigate_with_retry(page, url)
        return page

    async def _open_cdp_session(self) -> CDPSession | None:
        context = self._context
        if context is None:
            return None
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            if self._cdp is None:
                self._cdp = await context.new_cdp_session(page)
            return self._cdp
        except Error as exc:
            self.logger.warning("Failed to open CDP session", error=str(exc))
            self._cdp = None
            return None

    def _on_new_page(self, page: Page) -> None:
        if self._guard is None or not self._guard.is_foreign(page):
            return
        task = asyncio.create_task(self._close_foreign(page))
        self._guard_tasks.add(task)
        task.add_done_callback(self._guard_tasks.discard)

    async def _close_foreign(self, page: Page) -> None:
        self.logger.info("Closing a tab opened by the user in the locked window")
        try:
            await page.close()
        except Error as exc:
            self.logger.warning("Failed to close foreign page", error=str(exc))

    async def drain_guard_tasks(self) -> None:
        if self._guard_tasks:
            await asyncio.gather(*self._guard_tasks, return_exceptions=True)

    async def lock_window(self, page: BrowserPage, allowed_host: str) -> None:
        raw = page.raw_page
        guard = SinglePageGuard(allowed_host)
        guard.lock(raw)
        self._guard = guard
        try:
            await raw.route("**/*", guard.guard_route)
        except Error as exc:
            self.logger.warning("Failed to install navigation guard", error=str(exc))

    async def unlock_window(self) -> None:
        guard = self._guard
        if guard is None:
            return
        raw = guard.locked_page
        if raw is not None:
            try:
                await raw.unroute("**/*", guard.guard_route)
            except Error as exc:
                self.logger.warning("Failed to remove navigation guard", error=str(exc))
        guard.unlock()
        self._guard = None

    async def show_window(self) -> None:
        await self._window.show_near_app()

    async def hide_window(self) -> None:
        await self._window.hide()

    async def stop(self) -> None:
        self.logger.info("Stopping browser")
        if self._context is not None:
            await self._context.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._context = None
        self._playwright = None

    async def _navigate_with_retry(self, page: BrowserPage, url: str) -> None:
        raw = page.raw_page
        for attempt in range(MAX_ATTEMPTS):
            try:
                self.logger.info("Navigating page", url=url, attempt=attempt)
                await raw.goto(url)
                return
            except Exception as e:
                if not isinstance(e, Error):
                    raise
                self.logger.error(
                    "Failed to navigate page", url=url, attempt=attempt, error=str(e)
                )
                if attempt == MAX_ATTEMPTS - 1:
                    raise BrowserNetworkError() from e
                self.logger.info("Sleep before next retry", url=url, delay=RETRY_DELAY)
                await asyncio.sleep(RETRY_DELAY)

    async def new_page(self, url: str) -> BrowserPage:
        await self.ensure_started()
        if self._context is None:
            raise RuntimeError("BrowserCore is not started")
        for attempt in range(MAX_ATTEMPTS):
            page: Page | None = None
            try:
                self.logger.info("Opening page: ", url=url, attempt=attempt)
                page = await self._context.new_page()
                await page.goto(url)
                return BrowserPage(page)
            except Exception as e:
                if page is not None:
                    await page.close()
                if not isinstance(e, Error):
                    raise
                self.logger.error(
                    "Failed to open page", url=url, attempt=attempt, error=str(e)
                )
                if attempt == MAX_ATTEMPTS - 1:
                    raise BrowserNetworkError() from e
                self.logger.info("Sleep before next retry", url=url, delay=RETRY_DELAY)
                await asyncio.sleep(RETRY_DELAY)
        raise RuntimeError("Unreachable")

    async def cookies(self, base_url: str) -> list[Cookie]:
        await self.ensure_started()
        if self._context is None:
            return []
        try:
            return await self._context.cookies(base_url)
        except Exception as error:  # noqa: BLE001
            self.logger.warning(
                "Failed to read cookies (browser closed?)", error=str(error)
            )
            self._context = None
            return []

    async def clear_cookies(self) -> None:
        await self.ensure_started()
        if self._context is None:
            raise RuntimeError("BrowserCore is not started yet")
        await self._context.clear_cookies()
