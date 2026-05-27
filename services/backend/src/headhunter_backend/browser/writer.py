from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.page import BrowserPage
from enum import Enum
from dataclasses import dataclass
from headhunter_backend.log import get_logger
from headhunter_backend.browser.selectors import Selectors
from headhunter_backend.browser.text import normalize
import asyncio
import random

SUCCESS_PHRASES_NORMALIZED: tuple[str, ...] = tuple(
    normalize(p) for p in ("Вы откликнулись", "Вас пригласили")
)


class SubmitResultType(str, Enum):
    CAPTCHA = "captcha"
    SUBMITTED = "submitted"
    FAILED = "failed"


@dataclass(frozen=True)
class SubmitResult:
    type: SubmitResultType
    reason: str | None = None

    @classmethod
    def submitted(cls) -> "SubmitResult":
        return cls(type=SubmitResultType.SUBMITTED)

    @classmethod
    def captcha(cls) -> "SubmitResult":
        return cls(type=SubmitResultType.CAPTCHA)

    @classmethod
    def failed(cls, reason: str) -> "SubmitResult":
        return cls(type=SubmitResultType.FAILED, reason=reason)


class BrowserWriter:
    def __init__(
        self,
        core: BrowserCore,
        min_delay_ms: int,
        jitter_delay_ms: int,
        timeout: float = 5000,
    ):
        self._logger = get_logger(__name__)
        self._core = core
        self._jitter_delay_ms = jitter_delay_ms
        self._min_delay_ms = min_delay_ms
        self._timeout = timeout

    async def submit(
        self, vacancy_url: str, letter_text: str, selectors: Selectors
    ) -> SubmitResult:
        self._logger.info(
            f"Starting to submit: {vacancy_url}. Letter text: {letter_text}"
        )
        page: BrowserPage | None = None
        try:
            page = await self._core.new_page(url=vacancy_url)
            await page.wait_for_selector(
                selector=selectors.response.respond_button, timeout=self._timeout
            )
            await self._human_delay()

            if await self._captcha_present(page=page, selectors=selectors):
                return SubmitResult.captcha()

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
            return await self._verify(page=page, selectors=selectors)
        except Exception as e:
            self._logger.exception(f"Failed to submit: {vacancy_url}", error=str(e))
            return SubmitResult.failed(reason=str(e))
        finally:
            if page is not None:
                await page.close()

    async def _verify(self, page: BrowserPage, selectors: Selectors) -> SubmitResult:
        deadline = asyncio.get_running_loop().time() + self._timeout / 1000.0
        poll_interval_sec = 0.5

        while asyncio.get_running_loop().time() < deadline:
            if await self._captcha_present(page=page, selectors=selectors):
                return SubmitResult.captcha()

            body_text = await page.text_content("body")
            if body_text is not None:
                normalized = normalize(body_text)
                if any(phrase in normalized for phrase in SUCCESS_PHRASES_NORMALIZED):
                    self._logger.info("Submit verified by success phrase")
                    return SubmitResult.submitted()

            await asyncio.sleep(poll_interval_sec)

        return SubmitResult.failed(reason="verification timeout")

    async def _captcha_present(self, page: BrowserPage, selectors: Selectors) -> bool:
        if selectors.captcha.marker is None:
            return False
        return await page.query_selector(selector=selectors.captcha.marker) is not None

    async def _human_delay(self) -> None:
        jitter: float = random.uniform(-self._jitter_delay_ms, self._jitter_delay_ms)
        await asyncio.sleep((self._min_delay_ms + jitter) / 1000.0)
