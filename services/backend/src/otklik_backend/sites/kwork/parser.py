import json
from collections.abc import AsyncIterator
from typing import Any

from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.log import get_logger

BASE_URL = "https://kwork.ru"
_WANTS_KEY = '"wants":'


class KworkParser:
    def __init__(self, core: BrowserCore) -> None:
        self._core = core
        self._logger = get_logger(name=__name__)

    async def parse(self, search_page: BrowserPage) -> AsyncIterator[VacancyAPISchema]:
        self._logger.info(f"Start parsing Kwork projects: {search_page.get_url()}")
        wants = self._extract_wants(await search_page.content())
        self._logger.info(f"Found {len(wants)} Kwork projects on the page")
        seen: set[str] = set()
        for want in wants:
            vacancy = self._want_to_vacancy(want)
            if vacancy is None or vacancy.apply_link in seen:
                continue
            seen.add(vacancy.apply_link)
            yield vacancy

    def _extract_wants(self, html: str) -> list[dict[str, Any]]:
        index = html.find(_WANTS_KEY)
        if index < 0:
            self._logger.warning("No Kwork project data on the page")
            return []
        try:
            start = html.index("[", index)
            wants, _ = json.JSONDecoder().raw_decode(html, start)
        except (ValueError, json.JSONDecodeError) as error:
            self._logger.error(f"Failed to parse Kwork project data: {error}")
            return []
        return [want for want in wants if isinstance(want, dict)]

    def _want_to_vacancy(self, want: dict[str, Any]) -> VacancyAPISchema | None:
        want_id = want.get("id")
        title = want.get("name")
        description = want.get("description")
        if want_id is None or not title or not description:
            return None
        return VacancyAPISchema(
            title=str(title),
            apply_link=f"{BASE_URL}/projects/{want_id}",
            description=str(description),
            company_name=self._buyer(want),
            salary=self._budget(want),
        )

    @staticmethod
    def _buyer(want: dict[str, Any]) -> str | None:
        user = want.get("user")
        if isinstance(user, dict):
            username = user.get("username")
            if username:
                return str(username)
        return None

    @staticmethod
    def _budget(want: dict[str, Any]) -> str | None:
        try:
            price = int(float(want.get("priceLimit") or 0))
        except (TypeError, ValueError):
            return None
        if price <= 0:
            return None
        possible = want.get("possiblePriceLimit")
        try:
            possible_int = int(possible) if possible is not None else 0
        except (TypeError, ValueError):
            possible_int = 0
        if possible_int > price:
            return f"{price}–{possible_int} ₽"
        return f"до {price} ₽"
