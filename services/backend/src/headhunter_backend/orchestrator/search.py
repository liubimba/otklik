from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.page import BrowserPage
from headhunter_backend.browser.parser import Parser
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.browser.selectors import Selectors
from headhunter_backend.api.schemas import (
    VacanciesStartSearchRequestAPISchema,
    SearchStatusAPISchema,
)
from headhunter_backend.db.converters import vacancy_to_schema
from headhunter_backend.db.crud import (
    upsert_vacancy,
    create_search_history,
    update_search_history,
    get_settings,
    link_vacancy_to_search,
)
from headhunter_backend.db.models import VacancyORM
from headhunter_backend.log import get_logger
import asyncio
import urllib
import uuid
from enum import Enum
from headhunter_backend.api.events import SearchData, SearchWSEvent, VacancyWSEvent
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from dataclasses import dataclass, field
from statemachine import StateMachine
from statemachine.states import States
from datetime import datetime
from pydantic import HttpUrl
from headhunter_backend.orchestrator.exceptions import (
    FilterSessionNotFoundError,
    FilterSessionClosedError,
    SearchAlreadyRunningError,
    InvalidSearchURLError,
)
from pydantic import ValidationError


class SearchStateEvent(str, Enum):
    RUN = "run"
    CANCELED = "canceled"
    FINISHED = "finished"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class SearchStatusStateMachine(StateMachine):
    _ = States.from_enum(
        SearchStatusAPISchema,
        initial=SearchStatusAPISchema.PENDING,
        final=[
            SearchStatusAPISchema.CANCELED,
            SearchStatusAPISchema.FINISHED,
            SearchStatusAPISchema.FAILED,
            SearchStatusAPISchema.INTERRUPTED,
        ],
    )

    run = _.PENDING.to(_.RUNNING)
    canceled = _.RUNNING.to(_.CANCELED)
    finished = _.RUNNING.to(_.FINISHED)
    failed = _.RUNNING.to(_.FAILED)
    interrupt = _.PENDING.to(_.INTERRUPTED) | _.RUNNING.to(_.INTERRUPTED)


@dataclass
class SearchTask:
    id: str
    task: asyncio.Task[None]
    parsed_pages: int = 0
    parsed_count: int = 0
    state_machine: SearchStatusStateMachine = field(
        default_factory=SearchStatusStateMachine
    )


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
        self._core: BrowserCore = core
        self._parser: Parser = parser
        self._broadcaster: EventBroadcaster = broadcaster
        self._session_maker: async_sessionmaker[AsyncSession] = session_maker
        self._selectors: Selectors = selectors
        self._search_id: str | None = None
        self._search_queue: dict[str, SearchTask] = dict()
        self._filter_sessions: dict[str, BrowserPage] = dict()

    async def start_filter_session(self) -> str:
        page: BrowserPage = await self._core.new_page("https://hh.ru/search/vacancy")
        session_id = str(uuid.uuid4())
        self._filter_sessions[session_id] = page
        return session_id

    async def confirm_session(self, session_id: str) -> str:
        if session_id not in self._filter_sessions.keys():
            raise FilterSessionNotFoundError()
        page: BrowserPage = self._filter_sessions[session_id]
        if page.is_closed():
            del self._filter_sessions[session_id]
            raise FilterSessionClosedError()
        url: str = page.get_url()
        try:
            _ = VacanciesStartSearchRequestAPISchema(url=HttpUrl(url=url))
        except ValidationError as e:
            del self._filter_sessions[session_id]
            try:
                await page.close()
            except Exception:
                self._log.exception("Failed to close page after invalid URL")
            raise InvalidSearchURLError() from e
        del self._filter_sessions[session_id]
        await page.close()
        return url

    async def cancel_session(self, session_id: str) -> None:
        if session_id not in self._filter_sessions.keys():
            raise FilterSessionNotFoundError()
        page: BrowserPage = self._filter_sessions[session_id]
        if page.is_closed():
            del self._filter_sessions[session_id]
            raise FilterSessionClosedError()
        del self._filter_sessions[session_id]
        await page.close()

    def get_current_search_task(self) -> SearchTask | None:
        for task in self._search_queue.values():
            if task.state_machine.current_state_value.is_active():
                return task
        return None

    async def start_search(
        self, request: VacanciesStartSearchRequestAPISchema
    ) -> SearchTask:
        if len(self._search_queue) > 0:
            self._log.warning("Search is unavailable due to another is not completed")
            raise SearchAlreadyRunningError()
        async with self._session_maker() as session:
            settings = await get_settings(session=session)
        max_pages = (
            request.max_pages if request.max_pages is not None else settings.max_pages
        )
        max_vacancies = (
            request.max_vacancies
            if request.max_vacancies is not None
            else settings.max_vacancies
        )
        search_id: str = str(uuid.uuid4())
        task: asyncio.Task[None] = asyncio.create_task(
            self._run(
                search_id=search_id,
                url=str(request.url),
                max_pages=max_pages,
                max_vacancies=max_vacancies,
            )
        )
        self._search_queue[search_id] = SearchTask(id=search_id, task=task)
        self._log.info(
            "Queue searching",
            search_id=search_id,
            url=str(request.url),
            max_pages=max_pages,
            max_vacancies=max_vacancies,
        )
        async with self._session_maker() as session:
            await create_search_history(
                session=session,
                search_id=search_id,
                url=str(request.url),
                max_pages=max_pages,
                max_vacancies=max_vacancies,
                search_status=self._search_queue[
                    search_id
                ].state_machine.current_state_value,
            )
        return self._search_queue[search_id]

    async def cancel_search(self, search_id: str) -> bool:
        search_task: SearchTask | None = self.get_search_task(search_id=search_id)
        if search_task is None:
            return False
        already_cancelling = (
            search_task.task.cancelled() or search_task.task.cancelling() > 0
        )
        if not already_cancelling:
            search_task.task.cancel()
        try:
            await search_task.task
        except asyncio.CancelledError:
            pass
        except Exception:
            self._log.exception(
                "Search task raised during cancellation", search_id=search_id
            )
        return not already_cancelling

    async def shutdown(self) -> None:
        for search_task in self._search_queue.values():
            search_task.task.cancel()

    def get_search_task(self, search_id: str) -> SearchTask | None:
        return self._search_queue.get(search_id)

    async def _run(
        self,
        search_id: str,
        url: str,
        max_pages: int,
        max_vacancies: int,
    ) -> None:
        search_task: SearchTask | None = self.get_search_task(search_id=search_id)
        if search_task is None:
            self._log.exception("Failed to find", search_id=search_id)
            return
        search_page: BrowserPage = await self._core.new_page(url=url)
        self._log.info(
            "Run searching",
            search_id=search_id,
            url=url,
            max_pages=max_pages,
            max_vacancies=max_vacancies,
        )
        search_task.state_machine.send(SearchStateEvent.RUN.value)
        try:
            await self._update_search_history(search_task=search_task)
            while True:
                async for parsed_vacancy in self._parser.parse(
                    search_page=search_page,
                    selectors=self._selectors,
                ):
                    async with self._session_maker() as session:
                        vacancy_orm: VacancyORM = await upsert_vacancy(
                            session=session, vacancy=parsed_vacancy
                        )
                        await link_vacancy_to_search(
                            session=session,
                            search_id=search_id,
                            vacancy_id=vacancy_orm.id,
                        )
                        await session.commit()
                        await self._broadcaster.publish(
                            event=VacancyWSEvent(
                                data=vacancy_to_schema(row=vacancy_orm),
                                search_id=search_id,
                            )
                        )
                        search_task.parsed_count += 1
                        await self._publish_event(search_task=search_task)
                        await self._update_search_history(search_task=search_task)
                        if search_task.parsed_count >= max_vacancies:
                            break
                search_task.parsed_pages += 1
                await self._update_search_history(search_task=search_task)
                if (
                    search_task.parsed_count >= max_vacancies
                    or search_task.parsed_pages >= max_pages
                ):
                    break
                await self._open_next_page(search_page=search_page)
        except asyncio.exceptions.CancelledError as e:
            self._log.info(
                "Search thread has been cancelled", search_id=search_id, reason=str(e)
            )
            search_task.state_machine.send(SearchStateEvent.CANCELED.value)
        except Exception as e:
            self._log.exception("Caught an error durring search", error=str(e))
            search_task.state_machine.send(SearchStateEvent.FAILED.value)
        finally:
            await search_page.close()
        if search_task.state_machine.current_state_value.is_active():
            search_task.state_machine.send(SearchStateEvent.FINISHED.value)
        self._log.info(
            "Exit from search loop",
            search_id=search_id,
            parsed_pages=search_task.parsed_pages,
            parsed_count=search_task.parsed_count,
        )
        await self._update_search_history(search_task=search_task)
        await self._publish_event(search_task=search_task)
        self._search_queue.pop(search_id, None)

    async def _publish_event(self, search_task: SearchTask) -> None:
        await self._broadcaster.publish(
            event=SearchWSEvent(
                data=SearchData(
                    search_id=search_task.id,
                    parsed_vacancies=search_task.parsed_count,
                    parsed_pages=search_task.parsed_pages,
                    status=search_task.state_machine.current_state_value,
                )
            )
        )

    async def _open_next_page(self, search_page: BrowserPage) -> None:
        """Navigate the search page to the next page of results."""
        parsed_url = urllib.parse.urlparse(search_page.get_url())
        query: dict[str, list[str]] = urllib.parse.parse_qs(parsed_url.query)

        next_page = int(query["page"][0]) + 1 if "page" in query else 1
        query["page"] = [str(next_page)]

        next_url = urllib.parse.urlunparse(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                urllib.parse.urlencode(query, doseq=True),
                parsed_url.fragment,
            )
        )
        self._log.info(f"Opening next search page: {next_url}")
        await search_page.goto(next_url)

    async def _update_search_history(self, search_task: SearchTask) -> None:
        async with self._session_maker() as session:
            if (
                search_task.state_machine.current_state_value
                == SearchStatusAPISchema.RUNNING
            ):
                await update_search_history(
                    session=session,
                    search_id=search_task.id,
                    parsed_pages=search_task.parsed_pages,
                    parsed_vacancies=search_task.parsed_count,
                    status=search_task.state_machine.current_state_value,
                )
            else:
                await update_search_history(
                    session=session,
                    search_id=search_task.id,
                    status=search_task.state_machine.current_state_value,
                    finished_at=datetime.now(),
                )
