import asyncio
import urllib.parse
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from statemachine import StateMachine
from statemachine.states import States

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.schemas import SearchStatusAPISchema
from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.core.events import SearchData, SearchWSEvent, VacancyWSEvent
from otklik_backend.core.exceptions import DomainError
from otklik_backend.core.site import SiteParser
from otklik_backend.db.converters import vacancy_to_schema
from otklik_backend.db.models import VacancyORM
from otklik_backend.db.repositories.search_history import SearchHistoryRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.log import get_logger
from otklik_backend.orchestrator.exceptions import SearchAlreadyRunningError


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
class SearchSessionTask:
    id: str
    task: asyncio.Task[None]
    parsed_pages: int = 0
    parsed_count: int = 0
    state_machine: SearchStatusStateMachine = field(
        default_factory=SearchStatusStateMachine
    )

    @property
    def is_active(self) -> bool:
        return not self.state_machine.is_terminated


class SearchSession:
    def __init__(
        self,
        core: BrowserCore,
        session_maker: async_sessionmaker[AsyncSession],
        broadcaster: EventBroadcaster,
        parser: SiteParser,
        max_pages: int,
        max_vacancies: int,
    ) -> None:
        self._id = str(uuid.uuid4())
        self._log = get_logger(self.__class__.__name__)
        self._core = core
        self._session_maker = session_maker
        self._broadcaster = broadcaster
        self._parser = parser
        self._max_pages = max_pages
        self._max_vacancies = max_vacancies
        self._search_task: SearchSessionTask | None = None

        self._log.info("Issued new search session", id=self._id)

    @property
    def id(self) -> str:
        return self._id

    async def run(self, url: str) -> SearchSessionTask:
        self._log.info(
            "Queuing search",
            search_id=self._id,
            url=url,
            max_pages=self._max_pages,
            max_vacancies=self._max_vacancies,
        )
        if self._search_task is not None:
            raise SearchAlreadyRunningError()

        # Insert before spawning the task: _run()'s first act is to write RUNNING
        # onto this row, and SearchHistoryRepository.update() silently no-ops on a
        # missing row. Racing the INSERT left the run stuck at `pending` in the DB.
        async with self._session_maker() as session:
            self._log.info("Inserting search history into database")
            await SearchHistoryRepository.create(
                session=session,
                search_id=self._id,
                url=url,
                max_pages=self._max_pages,
                max_vacancies=self._max_vacancies,
                search_status=SearchStatusAPISchema.PENDING,
            )

        asyncio_task: asyncio.Task[None] = asyncio.create_task(self._run(url=url))
        search_task = SearchSessionTask(id=self._id, task=asyncio_task)
        self._search_task = search_task

        return search_task

    async def cancel(self) -> bool:
        if self._search_task is None:
            return False

        already_cancelling = (
            self._search_task.task.cancelled()
            or self._search_task.task.cancelling() > 0
        )
        if not already_cancelling:
            self._search_task.task.cancel()

        try:
            await self._search_task.task
        except asyncio.CancelledError:
            pass
        except Exception:
            self._log.exception(
                "Search task raised during cancellation", search_id=self._id
            )

        return not already_cancelling

    def get_search_task(self) -> SearchSessionTask | None:
        return self._search_task

    @classmethod
    async def execute(
        cls,
        url: str,
        core: BrowserCore,
        session_maker: async_sessionmaker[AsyncSession],
        broadcaster: EventBroadcaster,
        parser: SiteParser,
        max_pages: int,
        max_vacancies: int,
    ) -> Self:
        session = cls(
            core=core,
            session_maker=session_maker,
            broadcaster=broadcaster,
            parser=parser,
            max_pages=max_pages,
            max_vacancies=max_vacancies,
        )
        await session.run(url=url)
        return session

    async def _run(self, url: str) -> None:
        assert (
            self._search_task is not None
        ), "_run() called before _search_task was assigned"
        task = self._search_task

        self._log.info(
            "Running search",
            search_id=self._id,
            url=url,
            max_pages=self._max_pages,
            max_vacancies=self._max_vacancies,
        )
        # RUNNING before the first navigation: opening the page can already fail,
        # and `failed`/`canceled` are only reachable from RUNNING. Leaving the
        # transition until after new_page() stranded a dead search in PENDING —
        # forever `is_active`, so every later start hit SearchAlreadyRunningError.
        task.state_machine.send(SearchStateEvent.RUN.value)
        search_page: BrowserPage | None = None
        error: str | None = None

        try:
            await self._update_search_history(task)
            # Announce the run immediately. Clients (the История tab) refresh off
            # search_event; without this they only learn a run exists once the
            # parse loop emits its first vacancy.
            await self._publish_search_event(task)
            search_page = await self._core.new_page(url=url)
            await self._search_loop(task, search_page)
        except asyncio.CancelledError as exc:
            self._log.info("Search cancelled", search_id=self._id, reason=str(exc))
            task.state_machine.send(SearchStateEvent.CANCELED.value)
        except Exception as exc:
            self._log.exception("Error during search", search_id=self._id)
            error = self._describe(exc)
            task.state_machine.send(SearchStateEvent.FAILED.value)
        finally:
            if search_page is not None:
                await search_page.close()

        if task.is_active:
            task.state_machine.send(SearchStateEvent.FINISHED.value)

        self._log.info(
            "Exiting search loop",
            search_id=self._id,
            parsed_pages=task.parsed_pages,
            parsed_count=task.parsed_count,
        )
        await self._update_search_history(task, error=error)
        await self._publish_search_event(task)

    @staticmethod
    def _describe(exc: Exception) -> str:
        """A message fit for the История tab: domain errors carry a human-readable
        `detail`, everything else falls back to its own text."""
        if isinstance(exc, DomainError):
            return exc.detail
        return str(exc) or exc.__class__.__name__

    async def _search_loop(
        self, task: SearchSessionTask, search_page: BrowserPage
    ) -> None:
        while True:
            async for parsed_vacancy in self._parser.parse(
                search_page=search_page,
            ):
                async with self._session_maker() as session:
                    vacancy_orm: VacancyORM = await VacancyRepository.upsert(
                        session=session, vacancy=parsed_vacancy
                    )
                    await VacancyRepository.link_to_search(
                        session=session,
                        search_id=self._id,
                        vacancy_id=vacancy_orm.id,
                    )
                    await session.commit()

                await self._broadcaster.publish(
                    event=VacancyWSEvent(
                        data=vacancy_to_schema(row=vacancy_orm),
                        search_id=self._id,
                    )
                )
                task.parsed_count += 1
                await self._publish_search_event(task)
                await self._update_search_history(task)

                if task.parsed_count >= self._max_vacancies:
                    break

            task.parsed_pages += 1
            await self._update_search_history(task)

            if (
                task.parsed_count >= self._max_vacancies
                or task.parsed_pages >= self._max_pages
            ):
                break

            await self._open_next_page(search_page)

    async def _open_next_page(self, search_page: BrowserPage) -> None:
        parsed_url = urllib.parse.urlparse(search_page.get_url())
        query: dict[str, list[str]] = urllib.parse.parse_qs(parsed_url.query)

        try:
            current_page = int(query["page"][0]) if "page" in query else 0
        except (ValueError, IndexError):
            self._log.warning("Could not parse current page number, defaulting to 0")
            current_page = 0

        query["page"] = [str(current_page + 1)]
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
        self._log.info("Opening next search page", url=next_url)
        await search_page.goto(next_url)

    async def _publish_search_event(self, task: SearchSessionTask) -> None:
        await self._broadcaster.publish(
            event=SearchWSEvent(
                data=SearchData(
                    search_id=task.id,
                    parsed_vacancies=task.parsed_count,
                    parsed_pages=task.parsed_pages,
                    status=task.state_machine.current_state_value,
                )
            )
        )

    async def _update_search_history(
        self, task: SearchSessionTask, error: str | None = None
    ) -> None:
        async with self._session_maker() as session:
            if task.state_machine.current_state_value == SearchStatusAPISchema.RUNNING:
                await SearchHistoryRepository.update(
                    session=session,
                    search_id=task.id,
                    parsed_pages=task.parsed_pages,
                    parsed_vacancies=task.parsed_count,
                    status=task.state_machine.current_state_value,
                )
            else:
                await SearchHistoryRepository.update(
                    session=session,
                    search_id=task.id,
                    status=task.state_machine.current_state_value,
                    finished_at=datetime.now(),
                    error=error,
                )
