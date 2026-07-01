import asyncio
import random

from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.page import BrowserPage
from headhunter_backend.core.site.result import SubmissionResult
from headhunter_backend.log import get_logger
from headhunter_backend.sites.hh_ru.selectors import HHRU_SELECTORS, Selectors
from headhunter_backend.sites.hh_ru.text import normalize

SUCCESS_PHRASES_NORMALIZED: tuple[str, ...] = tuple(
    normalize(p) for p in ("Вы откликнулись", "Вас пригласили")
)


class HHRUWriter:
    def __init__(
        self,
        core: BrowserCore,
        min_delay_ms: int,
        jitter_delay_ms: int,
        selectors: Selectors = HHRU_SELECTORS,
        timeout: float = 5000,
    ) -> None:
        self._logger = get_logger(__name__)
        self._core = core
        self._selectors = selectors
        self._jitter_delay_ms = jitter_delay_ms
        self._min_delay_ms = min_delay_ms
        self._timeout = timeout

    async def submit(self, vacancy_url: str, letter_text: str) -> SubmissionResult:
        self._logger.info(
            f"Starting to submit: {vacancy_url}. Letter text: {letter_text}"
        )
        selectors = self._selectors
        page: BrowserPage | None = None
        try:
            page = await self._core.new_page(url=vacancy_url)
            await page.wait_for_selector(
                selector=selectors.response.respond_button, timeout=self._timeout
            )
            await self._human_delay()

            if await self._captcha_present(page=page):
                return SubmissionResult.captcha()

            await page.click(
                selector=selectors.response.open_letter_textarea_button,
                timeout=self._timeout,
            )
            await page.wait_for_selector(
                selector=selectors.response.letter_textarea, timeout=self._timeout
            )
            await self._human_delay()
            await page.fill(
                selector=selectors.response.letter_textarea,
                text=letter_text,
                timeout=self._timeout,
            )
            await self._human_delay()

            await page.click(
                selector=selectors.response.respond_button, timeout=self._timeout
            )
            return await self._verify(page=page)
        except Exception as e:
            self._logger.exception(f"Failed to submit: {vacancy_url}", error=str(e))
            return SubmissionResult.failed(reason=str(e))
        finally:
            if page is not None:
                await page.close()

    async def _verify(self, page: BrowserPage) -> SubmissionResult:
        deadline = asyncio.get_running_loop().time() + self._timeout / 1000.0
        poll_interval_sec = 0.5

        while asyncio.get_running_loop().time() < deadline:
            if await self._captcha_present(page=page):
                return SubmissionResult.captcha()

            body_text = await page.text_content("body")
            if body_text is not None:
                normalized = normalize(body_text)
                if any(phrase in normalized for phrase in SUCCESS_PHRASES_NORMALIZED):
                    self._logger.info("Submit verified by success phrase")
                    return SubmissionResult.submitted()

            await asyncio.sleep(poll_interval_sec)

        return SubmissionResult.failed(reason="verification timeout")

    async def _captcha_present(self, page: BrowserPage) -> bool:
        marker = self._selectors.captcha.marker
        if marker is None:
            return False
        return await page.query_selector(selector=marker) is not None

    async def _human_delay(self) -> None:
        jitter: float = random.uniform(-self._jitter_delay_ms, self._jitter_delay_ms)
        await asyncio.sleep((self._min_delay_ms + jitter) / 1000.0)
