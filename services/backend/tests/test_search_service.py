import asyncio
import pytest
from collections.abc import AsyncIterator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from pydantic import HttpUrl

from otklik_backend.orchestrator.search import (
    SearchService,
    SearchAlreadyRunningError,
)
from otklik_backend.orchestrator.exceptions import SearchSessionNotFoundError
from otklik_backend.api.schemas import (
    VacanciesStartSearchRequestAPISchema,
    SearchStatusAPISchema,
    VacancyAPISchema,
)
from otklik_backend.browser.exceptions import BrowserNetworkError
from otklik_backend.db.models import SearchHistoryORM, VacancyORM
from otklik_backend.core.events import SearchWSEvent, VacancyWSEvent

from tests.conftest import RecordingBroadcaster, wait_until


class FakeBrowserPage:
    def __init__(self, url: str) -> None:
        self._url = url
        self.closed = False

    def get_url(self) -> str:
        return self._url

    async def goto(self, url: str) -> None:
        self._url = url

    async def close(self) -> None:
        self.closed = True


class FakeBrowserCore:
    def __init__(self) -> None:
        self.opened_urls: list[str] = []
        self.pages: list[FakeBrowserPage] = []

    async def new_page(self, url: str) -> FakeBrowserPage:
        self.opened_urls.append(url)
        page = FakeBrowserPage(url)
        self.pages.append(page)
        return page


class UnreachableBrowserCore:
    def __init__(self) -> None:
        self.calls = 0

    async def new_page(self, url: str) -> FakeBrowserPage:
        self.calls += 1
        raise BrowserNetworkError()


class FakeParser:
    def __init__(self, batches: list[list[VacancyAPISchema]]) -> None:
        self._batches = list(batches)
        self.calls = 0

    async def parse(
        self, search_page: FakeBrowserPage
    ) -> AsyncIterator[VacancyAPISchema]:
        idx = self.calls
        self.calls += 1
        if idx >= len(self._batches):
            return
        for v in self._batches[idx]:
            yield v


class SlowParser:
    async def parse(
        self, search_page: FakeBrowserPage
    ) -> AsyncIterator[VacancyAPISchema]:
        await asyncio.sleep(10)
        yield _vacancy(0)


def _vacancy(i: int) -> VacancyAPISchema:
    return VacancyAPISchema(
        title=f"v{i}",
        apply_link=f"https://hh.ru/vacancy/{i}",
        description=f"desc {i}",
    )


def _filter(
    max_vacancies: int = 50, max_pages: int = 1
) -> VacanciesStartSearchRequestAPISchema:
    return VacanciesStartSearchRequestAPISchema(
        url=HttpUrl("https://hh.ru/search/vacancy"),
        max_vacancies=max_vacancies,
        max_pages=max_pages,
    )


@pytest.fixture
def fake_browser_core() -> FakeBrowserCore:
    return FakeBrowserCore()


def _make_service(
    browser: FakeBrowserCore,
    parser: FakeParser | SlowParser,
    broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> SearchService:
    return SearchService(
        core=browser,  # type: ignore[arg-type]
        parser=parser,  # type: ignore[arg-type]
        broadcaster=broadcaster,
        session_maker=session_factory,
    )


async def test_start_search_persists_and_finishes(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    parser = FakeParser([[_vacancy(1), _vacancy(2)]])
    svc = _make_service(
        fake_browser_core, parser, recording_broadcaster, session_factory
    )

    search_task = await svc.open_search_session(request=_filter(max_pages=1))
    search_id = search_task.id

    await search_task.task

    task = svc.find_search_task(search_id=search_id)
    assert task is not None
    assert task.parsed_count == 2
    assert task.state_machine.current_state_value == SearchStatusAPISchema.FINISHED

    async with session_factory() as session:
        count = (await session.execute(select(func.count(VacancyORM.id)))).scalar_one()
        assert count == 2

    search_events = [
        e for e in recording_broadcaster.events if isinstance(e, SearchWSEvent)
    ]
    assert len(search_events) >= 2
    assert search_events[-1].data.status == SearchStatusAPISchema.FINISHED


async def test_publishes_vacancy_new_event_per_parsed_vacancy(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    parser = FakeParser([[_vacancy(1), _vacancy(2)]])
    svc = _make_service(
        fake_browser_core, parser, recording_broadcaster, session_factory
    )

    search_task = await svc.open_search_session(request=_filter(max_pages=1))
    await search_task.task

    vacancy_events = [
        e for e in recording_broadcaster.events if isinstance(e, VacancyWSEvent)
    ]
    assert len(vacancy_events) == 2
    apply_links = {e.data.apply_link for e in vacancy_events}
    assert apply_links == {"https://hh.ru/vacancy/1", "https://hh.ru/vacancy/2"}


async def test_second_start_search_raises_already_running(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        fake_browser_core,
        SlowParser(),
        recording_broadcaster,
        session_factory,
    )

    await svc.open_search_session(request=_filter(max_pages=99))
    with pytest.raises(SearchAlreadyRunningError):
        await svc.open_search_session(request=_filter(max_pages=99))

    await svc.shutdown()


async def test_max_vacancies_cap_respected(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    parser = FakeParser([[_vacancy(1), _vacancy(2), _vacancy(3), _vacancy(4)]])
    svc = _make_service(
        fake_browser_core, parser, recording_broadcaster, session_factory
    )

    search_task = await svc.open_search_session(
        request=_filter(max_vacancies=2, max_pages=1)
    )
    search_id = search_task.id

    await search_task.task

    task = svc.find_search_task(search_id=search_id)
    assert task is not None
    assert task.parsed_count == 2


async def test_cancel_running_search(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        fake_browser_core,
        SlowParser(),
        recording_broadcaster,
        session_factory,
    )
    search_task = await svc.open_search_session(request=_filter())
    search_id = search_task.id

    await wait_until(
        lambda: search_task.state_machine.current_state_value
        == SearchStatusAPISchema.RUNNING
    )

    cancelled = await svc.cancel_search_session(search_id=search_id)
    assert cancelled is True
    await wait_until(
        lambda: search_task.state_machine.current_state_value
        == SearchStatusAPISchema.CANCELED
    )

    assert svc.find_search_task(search_id=search_id) is None
    assert (
        search_task.state_machine.current_state_value == SearchStatusAPISchema.CANCELED
    )


async def test_cancel_unknown_search_raises(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        fake_browser_core,
        FakeParser([]),
        recording_broadcaster,
        session_factory,
    )
    with pytest.raises(SearchSessionNotFoundError):
        await svc.cancel_search_session(search_id="does-not-exist")


async def test_get_search_task_unknown_returns_none(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        fake_browser_core,
        FakeParser([]),
        recording_broadcaster,
        session_factory,
    )
    assert svc.find_search_task(search_id="does-not-exist") is None


async def test_started_search_is_announced_before_any_vacancy_is_parsed(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        fake_browser_core, SlowParser(), recording_broadcaster, session_factory
    )

    search_task = await svc.open_search_session(request=_filter())

    def announced() -> bool:
        return any(isinstance(e, SearchWSEvent) for e in recording_broadcaster.events)

    await wait_until(announced)

    first = next(
        e for e in recording_broadcaster.events if isinstance(e, SearchWSEvent)
    )
    assert first.data.search_id == search_task.id
    assert first.data.status == SearchStatusAPISchema.RUNNING
    assert first.data.parsed_vacancies == 0

    await svc.shutdown()


async def test_running_search_is_persisted_as_running(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        fake_browser_core, SlowParser(), recording_broadcaster, session_factory
    )

    search_task = await svc.open_search_session(request=_filter())

    async def row_is_running() -> bool:
        async with session_factory() as session:
            row = await session.get(SearchHistoryORM, search_task.id)
            return row is not None and row.status == SearchStatusAPISchema.RUNNING

    await wait_until(row_is_running)

    await svc.shutdown()


async def test_search_fails_cleanly_when_the_page_cannot_be_opened(
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        UnreachableBrowserCore(),  # type: ignore[arg-type]
        FakeParser([]),
        recording_broadcaster,
        session_factory,
    )

    search_task = await svc.open_search_session(request=_filter())
    await search_task.task

    assert search_task.state_machine.current_state_value == SearchStatusAPISchema.FAILED
    assert not search_task.is_active

    search_events = [
        e for e in recording_broadcaster.events if isinstance(e, SearchWSEvent)
    ]
    assert search_events, "the UI must be told the search died"
    assert search_events[-1].data.status == SearchStatusAPISchema.FAILED


async def test_failed_search_is_persisted_with_its_error(
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        UnreachableBrowserCore(),  # type: ignore[arg-type]
        FakeParser([]),
        recording_broadcaster,
        session_factory,
    )

    search_task = await svc.open_search_session(request=_filter())
    await search_task.task

    async with session_factory() as session:
        row = await session.get(SearchHistoryORM, search_task.id)

    assert row is not None
    assert row.status == SearchStatusAPISchema.FAILED
    assert row.finished_at is not None
    assert row.error and "network" in row.error.lower()


async def test_failed_search_does_not_block_the_next_one(
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        UnreachableBrowserCore(),  # type: ignore[arg-type]
        FakeParser([]),
        recording_broadcaster,
        session_factory,
    )

    first = await svc.open_search_session(request=_filter())
    await first.task

    assert svc.get_current_search_task() is None

    second = await svc.open_search_session(request=_filter())
    await second.task
    assert second.id != first.id


async def test_shutdown_cancels_running_tasks(
    fake_browser_core: FakeBrowserCore,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    svc = _make_service(
        fake_browser_core,
        SlowParser(),
        recording_broadcaster,
        session_factory,
    )
    search_task = await svc.open_search_session(request=_filter())

    await asyncio.sleep(0.05)
    await svc.shutdown()
    await asyncio.sleep(0.05)

    task = svc.find_search_task(search_id=search_task.id)
    assert task is not None
    assert task.task.cancelled() or task.task.done()
