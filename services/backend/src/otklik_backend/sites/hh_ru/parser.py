import random
import urllib.parse
from asyncio import sleep
from collections.abc import AsyncIterator

from selectolax.parser import HTMLParser, Node

from otklik_backend.browser.core import BrowserCore
from otklik_backend.sites.hh_ru.mappers import (
    HHRUEmploymentTypeMapper,
    HHRUWorkFormatMapper,
)
from otklik_backend.browser.page import BrowserPage
from otklik_backend.sites.hh_ru.selectors import Selectors
from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.log import get_logger

# A hh.ru search result may link through an ad-tracking redirect instead of
# the vacancy itself; these markers locate the real URL on the SERP card.
_AD_HREF_PREFIX = "https://adsrv.hh.ru"


class HHRUParser:
    def __init__(self, core: BrowserCore, selectors: Selectors = None) -> None:  # type: ignore[assignment]
        from otklik_backend.sites.hh_ru.selectors import HHRU_SELECTORS

        self._core = core
        self._selectors = selectors if selectors is not None else HHRU_SELECTORS
        self._logger = get_logger(name=__name__)
        self._timeout_ms = 5000
        self._delay_sec = 1
        self._jitter_ms = 400
        self._work_format_mapper = HHRUWorkFormatMapper()
        self._employment_type_mapper = HHRUEmploymentTypeMapper()

    async def parse(self, search_page: BrowserPage) -> AsyncIterator[VacancyAPISchema]:
        selectors = self._selectors
        """Stream every vacancy from an open hh.ru search page, page by page.

        The caller hands over a search page with filters already applied and
        caps the stream by breaking out of the iteration. A second tab for
        vacancy details is opened lazily and closed once the stream ends.
        """
        self._logger.info(f"Start parsing search page: {search_page.get_url()}")

        parsed_links: set[str] = set()
        parsed_count = 0
        vacancy_page: BrowserPage | None = None

        try:
            while True:
                search_parser = HTMLParser(html=await search_page.content())
                vacancy_links = search_parser.css(selectors.search.apply_link)
                self._logger.info(
                    f"Found {len(vacancy_links)} vacancy links on search page"
                )

                if len(vacancy_links) == 0:
                    self._logger.info(
                        f"No vacancy links left, parsed {parsed_count} in total"
                    )
                    return

                for vacancy_link in vacancy_links:
                    try:
                        href = self._resolve_href_of_vacancy(
                            vacancy_link, selectors=selectors
                        )
                        if not self._check_href_of_vacancy(href, parsed_links):
                            continue

                        vacancy_page = await self._open_href_on_vacancy_page(
                            href, vacancy_page
                        )
                        vacancy = await self._parse_vacancy_page(
                            vacancy_page, href, selectors
                        )
                        if vacancy is not None:
                            parsed_count += 1
                            yield vacancy

                        await self._sleep_before_next_parse()
                    except Exception as error:
                        self._logger.error(
                            f"Skipped vacancy link {vacancy_link}: {error}"
                        )
        finally:
            if vacancy_page is not None:
                self._logger.info("Parsing finished, closing vacancy page")
                await vacancy_page.close()

    def _resolve_href_of_vacancy(
        self, vacancy_link: Node, selectors: Selectors
    ) -> str | None:
        """Return the vacancy URL of a SERP link, unwrapping ad redirects."""
        href = vacancy_link.attributes.get("href")
        if href is None:
            self._logger.error(f"Vacancy link has no 'href': {vacancy_link}")
            return None
        if href.startswith(_AD_HREF_PREFIX):
            self._logger.warning(f"Ad redirect in href, normalizing: {href}")
            return self._normalize_ad_href(vacancy_link, selectors=selectors) or href
        return href

    def _normalize_ad_href(
        self, vacancy_link: Node, selectors: Selectors
    ) -> str | None:
        """Recover the canonical vacancy URL hidden behind an adsrv.hh.ru link.

        Walks up to the SERP card and reads the vacancy id from its response
        link. Returns None when the card or the id cannot be found.
        """
        node: Node | None = vacancy_link.parent
        while node is not None:
            if node.css_matches(selector=selectors.search.vacancy_card):
                response_link = node.css_first(selectors.search.response_link_serp_card)
                if response_link is None:
                    self._logger.warning("SERP card has no response link")
                    return None
                response_href = response_link.attributes.get("href")
                if response_href is None:
                    self._logger.warning("SERP response link has no 'href'")
                    return None
                query = urllib.parse.parse_qs(
                    urllib.parse.urlparse(response_href).query
                )
                vacancy_ids = query.get("vacancyId")
                if not vacancy_ids:
                    self._logger.warning(
                        f"No 'vacancyId' in response link: {response_href}"
                    )
                    return None
                normalized = f"https://hh.ru/vacancy/{vacancy_ids[0]}"
                self._logger.info(f"Normalized ad href to: {normalized}")
                return normalized
            node = node.parent
        self._logger.warning("No SERP card found above the ad link")
        return None

    def _check_href_of_vacancy(self, href: str | None, parsed_links: set[str]) -> bool:
        """Return True for a new, parseable href and record it as seen."""
        if href is None:
            self._logger.error("Vacancy link has no href, skipping")
            return False
        if href in parsed_links:
            self._logger.info(f"Vacancy already parsed, skipping: {href}")
            return False
        parsed_links.add(href)
        return True

    async def _open_href_on_vacancy_page(
        self, href: str | None, vacancy_page: BrowserPage | None
    ) -> BrowserPage | None:
        """Open href in the detail tab, creating that tab on first use."""
        if href is None:
            return None
        if vacancy_page is None:
            self._logger.info(f"Opening vacancy page: {href}")
            vacancy_page = await self._core.new_page(href)
            await vacancy_page.set_viewport_size(width=100, height=1024)
        else:
            self._logger.info(f"Navigating vacancy page to: {href}")
            await vacancy_page.goto(href)
        return vacancy_page

    async def _parse_vacancy_page(
        self,
        vacancy_page: BrowserPage | None,
        href: str | None,
        selectors: Selectors,
    ) -> VacancyAPISchema | None:
        """Parse a single vacancy detail page into a VacancyAPISchema."""
        if vacancy_page is None or href is None:
            return None

        # title and description gate rendering — wait for them explicitly.
        title_element = await vacancy_page.wait_for_selector(
            selector=selectors.vacancy.title, timeout=self._timeout_ms
        )
        description_element = await vacancy_page.wait_for_selector(
            selector=selectors.vacancy.description, timeout=self._timeout_ms
        )
        title = (
            await title_element.text_content() if title_element is not None else None
        )
        description = (
            await description_element.text_content()
            if description_element is not None
            else None
        )
        if title is None or description is None:
            self._logger.error(f"No title/description for {href}, skipping vacancy")
            return None

        # The remaining fields are optional — read them in one selectolax pass.
        page_parser = HTMLParser(html=await vacancy_page.content())
        work_format_text = self._extract_text(
            page_parser, selectors.vacancy.work_format
        )
        employment_type_text = self._extract_text(
            page_parser, selectors.vacancy.employment_type
        )

        self._logger.info(f"Parsed vacancy: {href}")
        return VacancyAPISchema(
            title=title,
            apply_link=href,
            description=description,
            company_stars=self._extract_text(
                page_parser, selectors.vacancy.company_stars
            ),
            salary=self._extract_text(page_parser, selectors.vacancy.salary),
            company_name=self._extract_text(
                page_parser, selectors.vacancy.company_name
            ),
            work_location=self._extract_text(
                page_parser, selectors.vacancy.work_location
            ),
            updated_at=self._extract_text(page_parser, selectors.vacancy.updated_at),
            published_at=self._extract_text(
                page_parser, selectors.vacancy.published_at
            ),
            work_experience=self._extract_text(
                page_parser, selectors.vacancy.work_experience
            ),
            work_formats=self._work_format_mapper.from_raw(work_format_text),
            employment_types=self._employment_type_mapper.from_raw(
                employment_type_text
            ),
        )

    def _extract_text(self, parser: HTMLParser, selector: str | None) -> str | None:
        """Return the text of the first node matching selector, or None.

        Tolerates a None selector — an optional field with no selector yet.
        """
        if selector is None:
            return None
        node = parser.css_first(selector)
        return node.text() if node is not None else None

    async def _sleep_before_next_parse(self) -> None:
        """Sleep a short randomized delay to avoid a regular request cadence."""
        sleep_for = self._delay_sec + random.uniform(0, self._jitter_ms) / 1_000
        self._logger.info(f"Sleeping {sleep_for:.2f}s before next vacancy")
        await sleep(sleep_for)
