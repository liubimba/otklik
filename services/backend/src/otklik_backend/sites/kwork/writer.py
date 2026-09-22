import asyncio
import random
import re

from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.core.site.result import SubmissionResult
from otklik_backend.log import get_logger
from otklik_backend.sites.kwork.selectors import KWORK_RESPONSE, KworkResponseSelectors

OFFER_BUTTON_MISSING = "Кнопка «Предложить услугу» не найдена"
OFFER_FORM_MISSING = "Форма отклика не открылась"
OFFER_NOT_CONFIRMED = "Отклик не подтвердился"

DEFAULT_DELIVERY_DAYS = 3
ORDER_NAME_LIMIT = 70


def _numbers(text: str | None) -> list[int]:
    return [
        int(m.replace(" ", "").replace(" ", ""))
        for m in re.findall(r"\d[\d\s ]*", text or "")
    ]


class KworkWriter:
    def __init__(
        self,
        core: BrowserCore,
        min_delay_ms: int,
        jitter_delay_ms: int,
        selectors: KworkResponseSelectors = KWORK_RESPONSE,
        timeout: float = 10000,
    ) -> None:
        self._logger = get_logger(__name__)
        self._core = core
        self._selectors = selectors
        self._min_delay_ms = min_delay_ms
        self._jitter_delay_ms = jitter_delay_ms
        self._timeout = timeout

    async def submit(self, vacancy_url: str, letter_text: str) -> SubmissionResult:
        self._logger.info("Starting Kwork offer", vacancy_url=vacancy_url)
        try:
            page = await self._core.open_reusable_page("kwork_submit", vacancy_url)
            await self._human_delay()
            filled = await self.fill_offer(page, letter_text)
            if filled is not None:
                return filled
            self._logger.info("Submitting the Kwork offer")
            await page.click(self._selectors.submit_button, timeout=self._timeout)
            if not await self._confirmed(page):
                return SubmissionResult.failed(reason=OFFER_NOT_CONFIRMED)
            return SubmissionResult.submitted()
        except Exception as error:
            self._logger.exception("Failed to submit on Kwork", error=str(error))
            return SubmissionResult.failed(reason=str(error))

    async def fill_offer(
        self, page: BrowserPage, letter_text: str
    ) -> SubmissionResult | None:
        selectors = self._selectors
        if await page.query_selector(selectors.already_responded_marker) is not None:
            self._logger.info("Already responded on Kwork — nothing to do")
            return SubmissionResult.submitted()

        if not await page.click_first_visible(
            selectors.offer_button, timeout=self._timeout
        ):
            return SubmissionResult.failed(reason=OFFER_BUTTON_MISSING)

        try:
            await page.wait_for_selector(selectors.form_marker, timeout=self._timeout)
        except Exception:  # noqa: BLE001
            return SubmissionResult.failed(reason=OFFER_FORM_MISSING)

        await page.fill(selectors.message_editor, letter_text, timeout=self._timeout)
        await self._human_delay()

        price = await self._pick_price(page)
        await page.fill(selectors.price_input, str(price), timeout=self._timeout)

        await self._select_payment_type(page)
        await self._fill_order_name(page)
        await self._fill_delivery(page, DEFAULT_DELIVERY_DAYS)
        return None

    async def _select_payment_type(self, page: BrowserPage) -> None:
        if await page.click_first_visible(
            self._selectors.payment_type_option, timeout=self._timeout
        ):
            self._logger.info("Selected the Kwork payment order (whole)")

    async def _pick_price(self, page: BrowserPage) -> int:
        placeholder_nums: list[int] = []
        handle = await page.query_selector(self._selectors.price_input)
        if handle is not None:
            placeholder = await handle.get_attribute("placeholder")
            placeholder_nums = _numbers(placeholder)
        low = placeholder_nums[0] if placeholder_nums else 0
        high = placeholder_nums[-1] if len(placeholder_nums) >= 2 else 0

        desired = low
        budget = await page.text_content(self._selectors.buyer_budget)
        budget_nums = _numbers(budget)
        if budget_nums:
            desired = budget_nums[0]

        price = max(low, desired)
        if high:
            price = min(price, high)
        self._logger.info("Chosen Kwork price", price=price, low=low, high=high)
        return price

    async def _project_title(self, page: BrowserPage) -> str | None:
        for handle in await page.query_selector_all("h1"):
            text = ((await handle.text_content()) or "").strip()
            if text and "Предложить услугу" not in text:
                return text
        return None

    async def _fill_order_name(self, page: BrowserPage) -> None:
        try:
            handle = await page.query_selector(self._selectors.order_name_editor)
            if handle is None or not await handle.is_visible():
                return
            title = await self._project_title(page)
            if title:
                await page.fill(
                    self._selectors.order_name_editor,
                    title[:ORDER_NAME_LIMIT],
                    timeout=self._timeout,
                )
        except Exception as error:  # noqa: BLE001
            self._logger.info("Skipping Kwork order name", error=str(error))

    async def _fill_delivery(self, page: BrowserPage, days: int) -> None:
        try:
            await page.click(self._selectors.delivery_toggle, timeout=self._timeout)
            await self._human_delay()
            input_handle = await page.query_selector(self._selectors.delivery_input)
            if input_handle is None:
                self._logger.warning("Kwork delivery input not found")
                return
            await input_handle.type(str(days), delay=60)
            await self._human_delay()
            await page.raw_page.keyboard.press("Enter")
        except Exception as error:  # noqa: BLE001
            self._logger.warning("Failed to set Kwork delivery", error=str(error))

    async def _confirmed(self, page: BrowserPage) -> bool:
        for _ in range(4):
            await self._human_delay()
            handle = await page.query_selector(self._selectors.error_message)
            error = (await handle.text_content()) if handle is not None else None
            if error and error.strip():
                self._logger.warning("Kwork offer rejected", error=error.strip())
                return False
            if await page.query_selector(self._selectors.form_marker) is None:
                return True
        return False

    async def _human_delay(self) -> None:
        jitter = random.uniform(0, self._jitter_delay_ms)
        await asyncio.sleep((self._min_delay_ms + jitter) / 1000.0)
