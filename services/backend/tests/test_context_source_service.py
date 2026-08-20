from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.ai.source_tools import LLMSource
from otklik_backend.core.context_source import ContextSourceKind, ContextSourceStatus
from otklik_backend.db.repositories.context_sources import ContextSourceRepository
from otklik_backend.sources.fetchers import FetchedSource
from otklik_backend.sources.service import ContextSourceService


class FakeFetcher:
    def __init__(self, content: str | None = None, error: Exception | None = None):
        self.content = content
        self.error = error
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchedSource:
        self.calls.append(url)
        if self.error is not None:
            raise self.error
        assert self.content is not None
        return FetchedSource(content=self.content)


class FakeRegistry:
    def __init__(self) -> None:
        self.fetcher = FakeFetcher(content="snapshot text")
        self.aclose_calls = 0

    def for_url(self, url: str) -> FakeFetcher:
        return self.fetcher

    async def aclose(self) -> None:
        self.aclose_calls += 1


def make_service(
    session_factory: async_sessionmaker[AsyncSession], registry: FakeRegistry
) -> ContextSourceService:
    return ContextSourceService(session_maker=session_factory, registry=registry)  # type: ignore[arg-type]


async def test_add_stores_fetched_content_and_ok_status(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    source = await service.add(
        label="My blog", url="https://example.com/blog", description=None
    )

    assert source.content == "snapshot text"
    assert source.status == ContextSourceStatus.OK
    assert source.error is None
    assert source.kind == ContextSourceKind.WEB


async def test_add_records_error_and_does_not_raise(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    registry.fetcher = FakeFetcher(error=RuntimeError("boom"))
    service = make_service(session_factory, registry)

    source = await service.add(
        label="Broken", url="https://example.com/broken", description=None
    )

    assert source.status == ContextSourceStatus.ERROR
    assert source.content is None
    assert source.error is not None
    assert "boom" in source.error


async def test_add_marks_empty_snapshot_as_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    registry.fetcher = FakeFetcher(content="   \n\t  ")
    service = make_service(session_factory, registry)

    source = await service.add(
        label="YouTrack", url="https://youtrack.example/issues", description=None
    )

    assert source.status == ContextSourceStatus.ERROR
    assert source.content is None
    assert source.error is not None and source.error.strip()


async def test_refresh_refetches_and_updates_status(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    registry.fetcher = FakeFetcher(error=RuntimeError("boom"))
    service = make_service(session_factory, registry)

    source = await service.add(
        label="Flaky", url="https://example.com/flaky", description=None
    )
    assert source.status == ContextSourceStatus.ERROR

    registry.fetcher = FakeFetcher(content="fixed content")
    refreshed = await service.refresh(source.id)

    assert refreshed is not None
    assert refreshed.status == ContextSourceStatus.OK
    assert refreshed.content == "fixed content"
    assert refreshed.error is None


async def test_refresh_returns_none_for_missing_source(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    assert await service.refresh(999) is None


async def test_refresh_all_refreshes_every_source_and_returns_count(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    await service.add(label="One", url="https://example.com/1", description=None)
    await service.add(label="Two", url="https://example.com/2", description=None)

    registry.fetcher = FakeFetcher(content="fresh")
    count = await service.refresh_all()

    assert count == 2
    sources = await service.list()
    assert all(s.content == "fresh" for s in sources)


async def test_list_returns_all_sources(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    await service.add(label="One", url="https://example.com/1", description=None)
    await service.add(label="Two", url="https://example.com/2", description=None)

    sources = await service.list()
    assert {s.label for s in sources} == {"One", "Two"}


async def test_delete_removes_source(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    source = await service.add(
        label="Gone", url="https://example.com/gone", description=None
    )

    assert await service.delete(source.id) is True

    async with session_factory() as session:
        assert (
            await ContextSourceRepository.get_by_id(
                session=session, source_id=source.id
            )
            is None
        )
    assert await service.list() == []


async def test_delete_returns_false_for_missing_source(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    assert await service.delete(999) is False


async def test_update_without_url_change_keeps_kind_and_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    source = await service.add(
        label="Original", url="https://example.com/page", description=None
    )
    registry.fetcher.calls.clear()

    updated = await service.update(
        source.id,
        label="Renamed",
        url="https://example.com/page",
        description="new desc",
    )

    assert updated is not None
    assert updated.label == "Renamed"
    assert updated.description == "new desc"
    assert updated.kind == ContextSourceKind.WEB
    assert updated.content == "snapshot text"
    assert registry.fetcher.calls == []


async def test_update_with_changed_url_refetches_and_redetects_kind(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    source = await service.add(
        label="Original", url="https://example.com/page", description=None
    )
    assert source.kind == ContextSourceKind.WEB

    registry.fetcher = FakeFetcher(content="github snapshot")
    updated = await service.update(
        source.id,
        label="Original",
        url="https://github.com/octocat",
        description=None,
    )

    assert updated is not None
    assert updated.url == "https://github.com/octocat"
    assert updated.kind == ContextSourceKind.GITHUB
    assert updated.content == "github snapshot"
    assert updated.status == ContextSourceStatus.OK


async def test_update_returns_none_for_missing_source(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    result = await service.update(
        999, label="X", url="https://example.com/x", description=None
    )
    assert result is None


async def test_init_sets_logger_before_first_use(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    assert service._log is not None


async def test_aclose_delegates_to_registry_and_keeps_logger(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)
    log_before = service._log

    await service.aclose()

    assert registry.aclose_calls == 1
    assert service._log is log_before


async def test_list_ok_for_llm_returns_only_ok_sources_as_llm_sources(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registry = FakeRegistry()
    service = make_service(session_factory, registry)

    await service.add(label="One", url="https://example.com/1", description="d1")
    await service.add(label="Two", url="https://example.com/2", description=None)
    registry.fetcher = FakeFetcher(error=RuntimeError("boom"))
    await service.add(
        label="Broken", url="https://example.com/broken", description=None
    )

    sources = await service.list_ok_for_llm()

    assert len(sources) == 2
    assert all(isinstance(s, LLMSource) for s in sources)
    assert {s.content for s in sources} == {"snapshot text"}
    assert {s.label for s in sources} == {"One", "Two"}
