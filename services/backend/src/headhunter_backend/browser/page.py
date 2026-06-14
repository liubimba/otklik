from headhunter_backend.log import get_logger
from patchright.async_api import Page, ElementHandle, TimeoutError
from typing import List
from headhunter_backend.browser.exceptions import (
    ClosePageTimeoutError,
    OpenPageTimeoutError,
)


class BrowserPage:
    def __init__(self, context: Page) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._context = context

    async def goto(self, url: str) -> None:
        try:
            self._logger.info("Navigating to page: ", url=url)
            await self._context.goto(url)
        except TimeoutError as e:
            raise OpenPageTimeoutError() from e

    def get_url(self) -> str:
        return self._context.url

    def is_closed(self) -> bool:
        return self._context.is_closed()

    async def close(self) -> None:
        try:
            self._logger.info("Closing page")
            await self._context.close()
        except TimeoutError as e:
            raise ClosePageTimeoutError() from e

    async def click(self, selector: str, timeout: float | None = None) -> None:
        self._logger.info("Click", selector=selector, timeout=timeout)
        await self._context.click(selector=selector, timeout=timeout)

    async def fill(
        self, selector: str, text: str, timeout: float | None = None
    ) -> None:
        self._logger.info("Fill", selector=selector, text=text, timeout=timeout)
        await self._context.fill(selector=selector, value=text, timeout=timeout)

    async def bring_to_front(self) -> None:
        self._logger.info("Bringing page to front")
        await self._context.bring_to_front()

    async def content(self) -> str:
        return await self._context.content()

    async def text_content(self, selector: str) -> str | None:
        return await self._context.text_content(selector=selector)

    async def wait_for_selector(
        self, selector: str | None, timeout: float | None = None
    ) -> ElementHandle | None:
        if selector is None:
            return None
        return await self._context.wait_for_selector(selector=selector, timeout=timeout)

    async def set_viewport_size(self, width: int, height: int) -> None:
        old_width: int | None = (
            None
            if self._context.viewport_size is None
            else self._context.viewport_size.get("width")
        )
        old_height: int | None = (
            None
            if self._context.viewport_size is None
            else self._context.viewport_size.get("height")
        )

        self._logger.info(
            "Change viewport: ",
            old_width=old_width,
            new_width=width,
            old_height=old_height,
            new_height=height,
        )
        await self._context.set_viewport_size({"width": width, "height": height})

    async def query_selector(self, selector: str) -> ElementHandle | None:
        return await self._context.query_selector(selector=selector)

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        return await self._context.query_selector_all(selector=selector)
