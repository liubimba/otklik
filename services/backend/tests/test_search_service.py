import asyncio
import pytest
from collections.abc import AsyncIterator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from pydantic import HttpUrl

from headhunter_backend.orchestrator.search import (
    SearchService,
    SearchAlreadyRunningError,
)
from headhunter_backend.api.schemas import (
    VacanciesStartSearchRequestAPISchema,
    SearchStatusAPISchema,
    VacancyAPISchema,
)
from headhunter_backend.browser.selectors import HHRU_SELECTORS, Selectors
from headhunter_backend.db.models import VacancyORM
from headhunter_backend.api.events import SearchWSEvent, VacancyWSEvent

from tests.conftest import RecordingBroadcaster, wait_until


# ─ Fakes ─────────────────────────────────────────────────────────────


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


class FakeParser:
    """Возвращает разную пачку вакансий на каждом вызове parse() — имитирует страницы."""

    def __init__(self, batches: list[list[VacancyAPISchema]]) -> None:
        self._batches = list(batches)
        self.calls = 0

    async def parse(
        self, search_page: FakeBrowserPage, selectors: Selectors
    ) -> AsyncIterator[VacancyAPISchema]:
        idx = self.calls
        self.calls += 1
        if idx >= len(self._batches):
            return
        for v in self._batches[idx]:
            yield v


class SlowParser:
    """Зависает навсегда — для тестов cancel/shutdown."""

    async def parse(
        self, search_page: FakeBrowserPage, selectors: Selectors
    ) -> AsyncIterator[VacancyAPISchema]:
        await asyncio.sleep(10)
        yield _vacancy(0)  # никогда не доходит


# ─ Helpers ───────────────────────────────────────────────────────────


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
        selectors=HHRU_SELECTORS,
    )


# ─ Tests ─────────────────────────────────────────────────────────────


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

    task = svc.get_search_task(search_id=search_id)
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
    """SearchService must publish a VacancyWSEvent after each upsert_vacancy.
    Without it AutoApplyService never gets triggered and UI VacancyList never
    refreshes live."""
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

    task = svc.get_search_task(search_id=search_id)
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

    # Дать таску стартануть (state_machine перешёл в RUNNING)
    await wait_until(
        lambda: search_task.state_machine.current_state_value
        == SearchStatusAPISchema.RUNNING
    )

    cancelled = await svc.cancel_search_session(search_id=search_id)
    assert cancelled is True
    # CancelledError → state_machine.send(CANCELED) в except-блоке
    await wait_until(
        lambda: search_task.state_machine.current_state_value
        == SearchStatusAPISchema.CANCELED
    )

    task = svc.get_search_task(search_id=search_id)
    assert task is not None
    assert task.state_machine.current_state_value == SearchStatusAPISchema.CANCELED


async def test_cancel_unknown_search_returns_false(
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
    assert await svc.cancel_search_session(search_id="does-not-exist") is False


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
    assert svc.get_search_task(search_id="does-not-exist") is None


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

    task = svc.get_search_task(search_id=search_task.id)
    assert task is not None
    assert task.task.cancelled() or task.task.done()
