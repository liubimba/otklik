import asyncio
import random

from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.core.site.result import SubmissionResult
from otklik_backend.log import get_logger
from otklik_backend.sites.habr.selectors import HABR_SELECTORS, HabrSelectors

RESPOND_BUTTON_MISSING = "Кнопка «Откликнуться» не найдена"
RESPONSE_NOT_CONFIRMED = "Отклик не подтвердился"
LETTER_NOT_SAVED = "Сопроводительное письмо не сохранилось"


class HabrWriter:
    def __init__(
        self,
        core: BrowserCore,
        min_delay_ms: int,
        jitter_delay_ms: int,
        selectors: HabrSelectors = HABR_SELECTORS,
        timeout: float = 8000,
    ) -> None:
        self._logger = get_logger(__name__)
        self._core = core
        self._selectors = selectors
        self._min_delay_ms = min_delay_ms
        self._jitter_delay_ms = jitter_delay_ms
        self._timeout = timeout

    async def submit(self, vacancy_url: str, letter_text: str) -> SubmissionResult:
        self._logger.info("Starting Habr submit", vacancy_url=vacancy_url)
        response = self._selectors.response
        page: BrowserPage | None = None
        try:
            page = await self._core.open_reusable_page("habr_submit", vacancy_url)
            await self._human_delay()

            if await self._already_responded(page):
                self._logger.info("Already responded on Habr — editing the letter")
                return await self._edit_letter(page, letter_text)

            clicked = await page.click_first_visible(
                response.respond_button, timeout=self._timeout
            )
            if not clicked:
                return SubmissionResult.failed(reason=RESPOND_BUTTON_MISSING)

            if not await self._response_confirmed(page):
                return SubmissionResult.failed(reason=RESPONSE_NOT_CONFIRMED)

            await self._attach_letter(page, letter_text)
            if not await self._letter_visible(page, letter_text):
                self._logger.warning("Habr response sent but the letter did not save")
                return SubmissionResult.failed(reason=LETTER_NOT_SAVED)
            return SubmissionResult.submitted()
        except Exception as error:  # noqa: BLE001
            self._logger.exception("Failed to submit on Habr", error=str(error))
            return SubmissionResult.failed(reason=str(error))

    async def _already_responded(self, page: BrowserPage) -> bool:
        return (
            await page.query_selector(self._selectors.response.already_responded_marker)
            is not None
        )

    async def _response_confirmed(self, page: BrowserPage) -> bool:
        response = self._selectors.response
        confirmation = (
            f"{response.success_marker}, "
            f"{response.letter_textarea}, "
            f"{response.already_responded_marker}"
        )
        try:
            await page.wait_for_selector(confirmation, timeout=self._timeout)
            return True
        except Exception:  # noqa: BLE001
            self._logger.warning("Habr response confirmation did not appear")
            return False

    async def _edit_letter(
        self, page: BrowserPage, letter_text: str
    ) -> SubmissionResult:
        response = self._selectors.response
        try:
            await page.click(response.view_response_button, timeout=self._timeout)
            await self._human_delay()
        except Exception as error:  # noqa: BLE001
            self._logger.info("View-response control absent", error=str(error))
        try:
            self._logger.info("Opening the Habr response editor")
            await page.click(response.edit_button, timeout=self._timeout)
            await page.wait_for_selector(
                response.letter_textarea, timeout=self._timeout
            )
            await page.fill(response.letter_textarea, letter_text)
            await self._human_delay()
            self._logger.info("Saving the edited Habr letter")
            await page.click(response.save_button, timeout=self._timeout)
        except Exception as error:  # noqa: BLE001
            self._logger.warning("Failed to edit the Habr letter", error=str(error))
        if not await self._letter_visible(page, letter_text):
            return SubmissionResult.failed(reason=LETTER_NOT_SAVED)
        return SubmissionResult.submitted()

    async def _attach_letter(self, page: BrowserPage, letter_text: str) -> bool:
        response = self._selectors.response
        try:
            await page.wait_for_selector(
                response.letter_textarea, timeout=self._timeout
            )
            await page.fill(response.letter_textarea, letter_text)
            await self._human_delay()
            return await page.click_first_visible(
                response.letter_submit_button, timeout=self._timeout
            )
        except Exception as error:  # noqa: BLE001
            self._logger.warning("Failed to attach Habr cover letter", error=str(error))
            return False

    async def _letter_visible(self, page: BrowserPage, letter_text: str) -> bool:
        await self._human_delay()
        probe = " ".join(letter_text.split())[:40]
        if not probe:
            return True
        content = " ".join((await page.content()).split())
        return probe in content

    async def _human_delay(self) -> None:
        jitter = random.uniform(0, self._jitter_delay_ms)
        await asyncio.sleep((self._min_delay_ms + jitter) / 1000.0)
