from headhunter_backend.log import get_logger
from patchright.async_api import Page


class BrowserPage:
    def __init__(self, context: Page) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._context = context

    async def goto(self, url: str) -> None:
        self._logger.info("Navigating to page: ", url=url)
        await self._context.goto(url)

    def get_url(self) -> str:
        return self._context.url

    async def close(self) -> None:
        self._logger.info("Closing page")
        await self._context.close()

    async def bring_to_front(self) -> None:
        self._logger.info("Bringing page to front")
        await self._context.bring_to_front()
