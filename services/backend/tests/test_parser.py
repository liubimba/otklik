import sys
from pathlib import Path
from otklik_backend.log import get_logger
import pytest

from otklik_backend.browser.core import BrowserCore
from otklik_backend.sites.hh_ru.parser import HHRUParser
from otklik_backend.sites.hh_ru.selectors import HHRU_SELECTORS
from otklik_backend.api.schemas import VacancyAPISchema

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="headful Chromium integration test, Linux desktop session only",
)

SEARCH_URL = "https://hh.ru/search/vacancy?text=python"

MOBILE_WIDTH = 375
MOBILE_HEIGHT = 1024

TARGET_COUNT = 60
LOGGER = get_logger("test_parser")


@pytest.mark.skip
async def test_parser_returns_fifty_vacancies(tmp_path: Path) -> None:
    browser = BrowserCore(profile_dir=tmp_path / "test-profile")
    await browser.start()

    vacancies: list[VacancyAPISchema] = []
    try:
        search_page = await browser.new_page("about:blank")
        await search_page.set_viewport_size(width=MOBILE_WIDTH, height=MOBILE_HEIGHT)
        await search_page.goto(SEARCH_URL)
        await search_page.wait_for_selector(HHRU_SELECTORS.search.apply_link)

        parser = HHRUParser(browser)

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
