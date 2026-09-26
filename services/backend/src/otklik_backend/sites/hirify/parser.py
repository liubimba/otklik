import asyncio
import random
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from selectolax.parser import HTMLParser

from otklik_backend.api.schemas import EmploymentType, VacancyAPISchema, WorkFormat
from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.log import get_logger

API_HOST = "api.hirify.me"
API_PATH = "/api/vacancies"
DETAIL_URL = "https://api.hirify.me/api/vacancies/{id}"
JOB_URL = "https://hirify.me/jobs/{slug}"

_WORK_FORMATS: dict[str, WorkFormat] = {
    "remote": WorkFormat.REMOTE,
    "onsite": WorkFormat.ONSITE,
    "hybrid": WorkFormat.HYBRID,
    "traveling": WorkFormat.TRAVELING,
}
_WORK_TYPES: dict[str, EmploymentType] = {
    "fulltime": EmploymentType.FULL_TIME,
    "parttime": EmploymentType.PART_TIME,
    "part_time": EmploymentType.PART_TIME,
    "contract": EmploymentType.CONTRACT,
    "internship": EmploymentType.INTERNSHIP,
    "rotational": EmploymentType.ROTATIONAL,
}
_HIDDEN_COMPANY = frozenset({"None", "NDA", ""})


class HirifyParser:
    def __init__(
        self, core: BrowserCore, client: httpx.AsyncClient | None = None
    ) -> None:
        self._core = core
        self._client = client
        self._logger = get_logger(name=__name__)
        self._delay_sec = 0.4
        self._jitter_ms = 300

    async def parse(self, search_page: BrowserPage) -> AsyncIterator[VacancyAPISchema]:
        api_url = self._to_api_url(search_page.get_url())
        self._logger.info("Fetching Hirify vacancies page", api_url=api_url)
        client = self._client or httpx.AsyncClient(timeout=20.0)
        owns_client = self._client is None
        try:
            for item in await self._fetch_list(client, api_url):
                try:
                    vacancy = await self._to_vacancy(client, item)
                except Exception as error:  # noqa: BLE001
                    self._logger.error("Skipped Hirify vacancy", error=str(error))
                    continue
                if vacancy is not None:
                    yield vacancy
                await self._sleep_before_next()
        finally:
            if owns_client:
                await client.aclose()

    def _to_api_url(self, page_url: str) -> str:
        query = urlparse(page_url).query
        return urlunparse(("https", API_HOST, API_PATH, "", query, ""))

    async def _fetch_list(
        self, client: httpx.AsyncClient, api_url: str
    ) -> list[dict[str, Any]]:
        response = await client.get(api_url, headers={"Accept": "application/json"})
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, list) else []

    async def _to_vacancy(
        self, client: httpx.AsyncClient, item: dict[str, Any]
    ) -> VacancyAPISchema | None:
        vacancy_id = item.get("id")
        slug = item.get("slug")
        if vacancy_id is None or not slug:
            return None

        detail = await self._fetch_detail(client, vacancy_id)
        source = detail if detail is not None else item
        description = self._strip_html(source.get("text"))
        title = item.get("title") or source.get("title")
        if not title or not description:
            self._logger.info("Skipping Hirify vacancy without title/description")
            return None

        return VacancyAPISchema(
            title=title,
            apply_link=JOB_URL.format(slug=slug),
            description=description,
            company_name=self._company(item.get("company_title")),
            salary=self._salary(item.get("salary")),
            work_formats=self._work_formats(item.get("work_format")),
            employment_types=self._employment_types(item.get("work_type")),
            work_experience=self._grades(item.get("grades")),
            already_responded=bool(item.get("has_applied")),
        )

    async def _fetch_detail(
        self, client: httpx.AsyncClient, vacancy_id: Any
    ) -> dict[str, Any] | None:
        try:
            response = await client.get(
                DETAIL_URL.format(id=vacancy_id),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as error:  # noqa: BLE001
            self._logger.warning(
                "Hirify detail fetch failed", vacancy_id=vacancy_id, error=str(error)
            )
            return None
        if not isinstance(payload, dict):
            return None
        inner = payload.get("data")
        return inner if isinstance(inner, dict) else payload

    @staticmethod
    def _strip_html(raw: Any) -> str:
        if not isinstance(raw, str) or not raw:
            return ""
        return HTMLParser(raw).text(separator="\n", strip=True)

    @staticmethod
    def _company(value: Any) -> str | None:
        if not isinstance(value, str) or value in _HIDDEN_COMPANY:
            return None
        return value

    @staticmethod
    def _salary(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _work_formats(raw: Any) -> list[WorkFormat]:
        if not isinstance(raw, list):
            return [WorkFormat.UNKNOWN]
        formats = [_WORK_FORMATS[v] for v in raw if v in _WORK_FORMATS]
        return formats or [WorkFormat.UNKNOWN]

    @staticmethod
    def _employment_types(raw: Any) -> list[EmploymentType]:
        mapped = _WORK_TYPES.get(raw) if isinstance(raw, str) else None
        return [mapped] if mapped is not None else [EmploymentType.UNKNOWN]

    @staticmethod
    def _grades(raw: Any) -> str | None:
        if not isinstance(raw, list):
            return None
        names = [
            g["name"]
            for g in raw
            if isinstance(g, dict) and isinstance(g.get("name"), str)
        ]
        return ", ".join(names) or None

    async def _sleep_before_next(self) -> None:
        await asyncio.sleep(self._delay_sec + random.uniform(0, self._jitter_ms) / 1000)
