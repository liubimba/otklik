import random
from asyncio import sleep
from collections.abc import AsyncIterator

from selectolax.parser import HTMLParser

from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.log import get_logger
from otklik_backend.sites.habr.mappers import (
    HabrEmploymentTypeMapper,
    HabrWorkFormatMapper,
)
from otklik_backend.sites.habr.selectors import HABR_SELECTORS, HabrSelectors

BASE_URL = "https://career.habr.com"
_CONDITIONS_TITLE = "условия"


class HabrParser:
    def __init__(
        self, core: BrowserCore, selectors: HabrSelectors = HABR_SELECTORS
    ) -> None:
        self._core = core
        self._selectors = selectors
        self._logger = get_logger(name=__name__)
        self._delay_sec = 1
        self._jitter_ms = 400
        self._work_format_mapper = HabrWorkFormatMapper()
        self._employment_type_mapper = HabrEmploymentTypeMapper()

    async def parse(self, search_page: BrowserPage) -> AsyncIterator[VacancyAPISchema]:
        selectors = self._selectors
        self._logger.info(f"Start parsing Habr search page: {search_page.get_url()}")

        search_parser = HTMLParser(html=await search_page.content())
        links = search_parser.css(selectors.search.title_link)
        self._logger.info(f"Found {len(links)} vacancy links on Habr search page")

        seen: set[str] = set()
        for link in links:
            try:
                href = self._resolve_href(link.attributes.get("href"))
                if href is None or href in seen:
                    continue
                seen.add(href)

                detail_page = await self._core.open_reusable_page("habr_vacancy", href)
                if detail_page is None:
                    continue
                vacancy = self._parse_detail(await detail_page.content(), href)
                if vacancy is not None:
                    yield vacancy

                await self._sleep_before_next()
            except Exception as error:  # noqa: BLE001
                self._logger.error(f"Skipped Habr vacancy {link}: {error}")

    def _resolve_href(self, href: str | None) -> str | None:
        if href is None:
            return None
        if href.startswith("http"):
            return href
        return f"{BASE_URL}{href}"

    def _parse_detail(self, html: str, url: str) -> VacancyAPISchema | None:
        parser = HTMLParser(html=html)
        selectors = self._selectors.vacancy

        title = self._text(parser, selectors.title)
        description = self._text(parser, selectors.description)
        if not title or not description:
            self._logger.error(f"No title/description for {url}, skipping")
            return None

        conditions = self._conditions_text(parser)
        return VacancyAPISchema(
            title=title,
            apply_link=url,
            description=description,
            company_name=self._text(parser, selectors.company_name),
            salary=self._text(parser, selectors.salary),
            work_formats=self._work_format_mapper.from_raw(conditions),
            employment_types=self._employment_type_mapper.from_raw(conditions),
        )

    def _conditions_text(self, parser: HTMLParser) -> str | None:
        for section in parser.css(self._selectors.vacancy.conditions_section):
            title = section.css_first(self._selectors.vacancy.section_title)
            if (
                title is not None
                and _CONDITIONS_TITLE in title.text(strip=True).lower()
            ):
                return section.text(strip=True)
        return None

    @staticmethod
    def _text(parser: HTMLParser, selector: str) -> str | None:
        node = parser.css_first(selector)
        if node is None:
            return None
        text = node.text(strip=True)
        return text or None

    async def _sleep_before_next(self) -> None:
        sleep_for = self._delay_sec + random.uniform(0, self._jitter_ms) / 1_000
        await sleep(sleep_for)
