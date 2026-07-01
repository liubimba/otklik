from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.schemas import VacanciesStartSearchRequestAPISchema
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.parser import Parser
from headhunter_backend.browser.selectors import Selectors
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator.exceptions import (
    FilterSessionNotFoundError,
    FilterSessionRunningAlreadyError,
    SearchAlreadyRunningError,
    SearchSessionNotFoundError,
)
from headhunter_backend.orchestrator.search.filter_session import FilterSession
from headhunter_backend.orchestrator.search.search_session import (
    SearchSession,
    SearchSessionTask,
)
from headhunter_backend.db.repositories.settings import SettingsRepository


class SearchService:
    def __init__(
        self,
        core: BrowserCore,
        parser: Parser,
        broadcaster: EventBroadcaster,
        session_maker: async_sessionmaker[AsyncSession],
        selectors: Selectors,
    ) -> None:
        self._log = get_logger(__name__)
        self._core = core
        self._parser = parser
        self._broadcaster = broadcaster
        self._session_maker = session_maker
        self._selectors = selectors
        self._filter_session: FilterSession | None = None
        self._search_session: SearchSession | None = None

    async def open_filter_session(self) -> str:
        if self._filter_session is not None:
            self._log.error(
                "Filter session already running", id=self._filter_session.id
            )
            raise FilterSessionRunningAlreadyError()

        self._filter_session = await FilterSession.execute(core=self._core)
        return self._filter_session.id

    async def confirm_filter_session(self, session_id: str) -> str:
        if self._filter_session is None or self._filter_session.id != session_id:
            raise FilterSessionNotFoundError()
        try:
            return await self._filter_session.confirm()
        finally:
            self._filter_session = None

    async def cancel_filter_session(self, session_id: str) -> None:
        if self._filter_session is None or self._filter_session.id != session_id:
            raise FilterSessionNotFoundError()
        await self._filter_session.cancel()
        self._filter_session = None

    def get_current_filter_session(self) -> str | None:
        if self._filter_session is None:
            return None
        return self._filter_session.id

    async def open_search_session(
        self, request: VacanciesStartSearchRequestAPISchema
    ) -> SearchSessionTask:
        # Чистим сессию если поиск уже завершился — чтобы можно было запустить новый
        if self._search_session is not None:
            task = self._search_session.get_search_task()
            if task is None or not task.is_active:
                self._search_session = None

        if self._search_session is not None:
            self._log.warning("Search already running")
            raise SearchAlreadyRunningError()

        async with self._session_maker() as session:
            settings = await SettingsRepository.get(session=session)

        max_pages = (
            request.max_pages if request.max_pages is not None else settings.max_pages
        )
        max_vacancies = (
            request.max_vacancies
            if request.max_vacancies is not None
            else settings.max_vacancies
        )

        self._search_session = await SearchSession.execute(
            url=str(request.url),
            core=self._core,
            session_maker=self._session_maker,
            broadcaster=self._broadcaster,
            parser=self._parser,
            selectors=self._selectors,
            max_pages=max_pages,
            max_vacancies=max_vacancies,
        )

        task = self._search_session.get_search_task()
        assert task is not None, "SearchSession.execute() must initialise the task"
        return task

    async def cancel_search_session(self, search_id: str) -> bool:
        if self._search_session is None or self._search_session.id != search_id:
            raise SearchSessionNotFoundError()

        cancelled = await self._search_session.cancel()
        self._search_session = None
        return cancelled

    def find_search_task(self, search_id: str) -> SearchSessionTask | None:
        if self._search_session is not None and self._search_session.id == search_id:
            return self._search_session.get_search_task()
        return None

    def get_current_search_task(self) -> SearchSessionTask | None:
        if self._search_session is None:
            return None
        task = self._search_session.get_search_task()
        return task if (task and task.is_active) else None

    async def shutdown(self) -> None:
        if self._search_session is not None:
            await self._search_session.cancel()
        if self._filter_session is not None:
            await self._filter_session.cancel()
