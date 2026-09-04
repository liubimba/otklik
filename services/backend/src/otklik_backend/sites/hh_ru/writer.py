import asyncio
import random

from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserFrame, BrowserPage
from otklik_backend.core.site.result import SubmissionResult
from otklik_backend.log import get_logger
from otklik_backend.sites.hh_ru.selectors import HHRU_SELECTORS, Selectors
from otklik_backend.sites.hh_ru.text import normalize

SUCCESS_PHRASES_NORMALIZED: tuple[str, ...] = tuple(
    normalize(p) for p in ("Вы откликнулись", "Вас пригласили")
)

MANDATORY_TEST_REASON = (
    "Работодатель требует пройти тест — откликнитесь на эту вакансию вручную"
)

LETTER_NOT_ATTACHED_REASON = (
    "Не удалось прикрепить сопроводительное письмо — отклик не отправлен"
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
            page = await self._core.open_reusable_page("submit", vacancy_url)

            await page.wait_for_selector(
                selector=selectors.vacancy.respond_link_top, timeout=self._timeout
            )
            await self._human_delay()
            await page.click(
                selector=selectors.vacancy.respond_link_top, timeout=self._timeout
            )

            await self._pass_relocation_gate(page=page)
            await self._human_delay()

            if await self._captcha_present(page=page):
                return SubmissionResult.captcha()

            flow = await self._detect_flow(page=page)
            if flow is None:
                self._logger.info("No response form inline, reloading to re-check")
                await page.goto(url=vacancy_url)
                flow = await self._detect_flow(page=page)
            self._logger.info("Detected response flow", flow=flow)
            if flow == "popup":
                return await self._submit_via_popup(page=page, letter_text=letter_text)
            if flow == "chat":
                return await self._attach_letter_via_chat(
                    page=page, letter_text=letter_text
                )
            return SubmissionResult.failed(reason="Форма отклика не появилась")
        except Exception as e:
            self._logger.exception(f"Failed to submit: {vacancy_url}", error=str(e))
            return SubmissionResult.failed(reason=str(e))

    async def _detect_flow(self, page: BrowserPage) -> str | None:
        response = self._selectors.response
        vacancy = self._selectors.vacancy
        deadline = asyncio.get_running_loop().time() + self._timeout / 1000.0
        while True:
            if await page.query_selector(selector=response.respond_button) is not None:
                return "popup"
            if await page.query_selector(selector=vacancy.chat_open) is not None:
                return "chat"
            if asyncio.get_running_loop().time() >= deadline:
                return None
            await asyncio.sleep(0.3)

    async def _submit_via_popup(
        self, page: BrowserPage, letter_text: str
    ) -> SubmissionResult:
        selectors = self._selectors
        if await self._mandatory_test_blocks_submission(page=page):
            return SubmissionResult.failed(reason=MANDATORY_TEST_REASON)

        await self._reveal_letter_field(page=page)
        await self._human_delay()
        await page.fill(
            selector=selectors.response.letter_textarea,
            text=letter_text,
            timeout=self._timeout,
        )
        await self._human_delay()

        if not await self._letter_attached(page=page, expected=letter_text):
            return SubmissionResult.failed(reason=LETTER_NOT_ATTACHED_REASON)

        await page.click(
            selector=selectors.response.respond_button, timeout=self._timeout
        )
        return await self._verify(page=page)

    async def _attach_letter_via_chat(
        self, page: BrowserPage, letter_text: str
    ) -> SubmissionResult:
        chat = self._selectors.chat
        await self._human_delay()
        await page.click(
            selector=self._selectors.vacancy.chat_open, timeout=self._timeout
        )
        frame = await page.wait_for_frame(
            url_marker=chat.frame_url_marker, timeout=self._timeout
        )
        if frame is None:
            return SubmissionResult.failed(reason="Чат отклика не открылся")

        await frame.wait_for_selector(
            selector=chat.add_cover_letter, timeout=self._timeout
        )
        await self._human_delay()
        await frame.click(selector=chat.add_cover_letter, timeout=self._timeout)

        await frame.wait_for_selector(selector=chat.letter_input, timeout=self._timeout)
        await self._human_delay()
        await frame.fill(
            selector=chat.letter_input, text=letter_text, timeout=self._timeout
        )
        await self._human_delay()

        value = await frame.input_value(selector=chat.letter_input)
        if letter_text.strip() not in value:
            self._logger.warning("Cover letter did not stick in the chat field")
            return SubmissionResult.failed(reason=LETTER_NOT_ATTACHED_REASON)

        await frame.click(selector=chat.send_message, timeout=self._timeout)
        return await self._verify_chat(frame=frame, letter_text=letter_text)

    async def _verify_chat(
        self, frame: BrowserFrame, letter_text: str
    ) -> SubmissionResult:
        lines = letter_text.strip().splitlines()
        probe = normalize(lines[0][:40]) if lines else ""
        deadline = asyncio.get_running_loop().time() + self._timeout / 1000.0
        while asyncio.get_running_loop().time() < deadline:
            html = await frame.content()
            if probe and probe in normalize(html):
                self._logger.info("Cover letter delivered to the response chat")
                return SubmissionResult.submitted()
            await asyncio.sleep(0.5)
        return SubmissionResult.failed(reason="Не удалось подтвердить письмо в чате")

    async def _verify(self, page: BrowserPage) -> SubmissionResult:
        deadline = asyncio.get_running_loop().time() + self._timeout / 1000.0
        poll_interval_sec = 0.5

        while asyncio.get_running_loop().time() < deadline:
            if await self._captcha_present(page=page):
                return SubmissionResult.captcha()

            await self._confirm_relocation_if_present(page=page)

            body_text = await page.text_content("body")
            if body_text is not None:
                normalized = normalize(body_text)
                if any(phrase in normalized for phrase in SUCCESS_PHRASES_NORMALIZED):
                    self._logger.info("Submit verified by success phrase")
                    return SubmissionResult.submitted()

            await asyncio.sleep(poll_interval_sec)

        return SubmissionResult.failed(reason="verification timeout")

    async def _mandatory_test_blocks_submission(self, page: BrowserPage) -> bool:
        marker = self._selectors.response.employer_test_marker
        return await page.query_selector(selector=marker) is not None

    async def _letter_attached(self, page: BrowserPage, expected: str) -> bool:
        stripped = expected.strip()
        if not stripped:
            return True
        try:
            value = await page.input_value(
                selector=self._selectors.response.letter_textarea,
                timeout=self._timeout,
            )
        except Exception as error:  # noqa: BLE001
            self._logger.warning(
                "Could not read back the cover letter field", error=str(error)
            )
            return False
        if stripped in value:
            return True
        self._logger.warning("Cover letter did not stick in the response field")
        return False

    async def _reveal_letter_field(self, page: BrowserPage) -> None:
        response = self._selectors.response
        if await page.query_selector(selector=response.letter_textarea) is not None:
            return
        if (
            await page.query_selector(selector=response.open_letter_textarea_button)
            is not None
        ):
            await page.click(
                selector=response.open_letter_textarea_button, timeout=self._timeout
            )
        await page.wait_for_selector(
            selector=response.letter_textarea, timeout=self._timeout
        )

    async def _pass_relocation_gate(self, page: BrowserPage) -> None:
        response = self._selectors.response
        vacancy = self._selectors.vacancy
        try:
            await page.wait_for_selector(
                selector=(
                    f"{response.relocation_confirm}, "
                    f"{response.respond_button}, "
                    f"{vacancy.chat_open}"
                ),
                timeout=self._timeout,
            )
        except Exception as error:  # noqa: BLE001
            self._logger.warning(
                "Neither the relocation modal nor the response form appeared",
                error=str(error),
            )
            return
        await self._confirm_relocation_if_present(page=page)

    async def _confirm_relocation_if_present(self, page: BrowserPage) -> None:
        confirm = self._selectors.response.relocation_confirm
        if await page.query_selector(selector=confirm) is None:
            return
        self._logger.info("Relocation warning shown, confirming the response")
        await page.click(selector=confirm, timeout=self._timeout)
        await self._human_delay()

    async def _captcha_present(self, page: BrowserPage) -> bool:
        marker = self._selectors.captcha.marker
        if marker is None:
            return False
        return await page.query_selector(selector=marker) is not None

    async def _human_delay(self) -> None:
        jitter: float = random.uniform(-self._jitter_delay_ms, self._jitter_delay_ms)
        await asyncio.sleep((self._min_delay_ms + jitter) / 1000.0)
