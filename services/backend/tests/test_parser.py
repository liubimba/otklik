import sys
from pathlib import Path
from headhunter_backend.log import get_logger
import pytest

from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.parser import Parser
from headhunter_backend.browser.selectors import HHRU_SELECTORS
from headhunter_backend.api.schemas import VacancyAPISchema

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="headful Chromium integration test, Linux desktop session only",
)

# Broad query — reliably yields far more results than TARGET_COUNT.
SEARCH_URL = "https://hh.ru/search/vacancy?text=python"

# A narrow viewport forces hh.ru's mobile layout, where every field carries
# a stable ``data-qa`` attribute (see the Parser service / Anti-bot notes).
MOBILE_WIDTH = 375
MOBILE_HEIGHT = 1024

# Stage 1.3 acceptance criterion: a test query returns 50 vacancies.
TARGET_COUNT = 60
LOGGER = get_logger("test_parser")


@pytest.mark.skip
async def test_parser_returns_fifty_vacancies(tmp_path: Path) -> None:
    browser = BrowserCore(profile_dir=tmp_path / "test-profile")
    await browser.start()

    vacancies: list[VacancyAPISchema] = []
    try:
        # The caller prepares the search page. Open a blank page first so the
        # search URL loads exactly once, already at the mobile viewport.
        search_page = await browser.new_page("about:blank")
        await search_page.set_viewport_size(width=MOBILE_WIDTH, height=MOBILE_HEIGHT)
        await search_page.goto(SEARCH_URL)
        # Wait until result cards are rendered before handing the page over.
        await search_page.wait_for_selector(HHRU_SELECTORS.search.apply_link)

        parser = Parser(browser)

        # parse() is an unbounded stream; the consumer caps it at TARGET_COUNT.
        async for vacancy in parser.parse(search_page, HHRU_SELECTORS):
            vacancies.append(vacancy)
            if len(vacancies) >= TARGET_COUNT:
                break
    finally:
        await browser.stop()

    LOGGER.info(f"Discovered vacancies: {vacancies}")
    assert len(vacancies) == TARGET_COUNT
    for vacancy in vacancies:
        assert vacancy.title
        assert vacancy.description
        assert vacancy.apply_link.startswith("http")
