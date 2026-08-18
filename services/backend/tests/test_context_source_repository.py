from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.core.context_source import ContextSourceKind, ContextSourceStatus
from otklik_backend.db.repositories.context_sources import ContextSourceRepository


async def test_create_and_get_by_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        created = await ContextSourceRepository.create(
            session=session,
            label="My GitHub",
            url="https://github.com/octocat",
            description="octocat profile",
            kind=ContextSourceKind.GITHUB,
        )
        source_id = created.id
        assert source_id is not None
        assert created.status == ContextSourceStatus.PENDING

    async with session_factory() as session:
        fetched = await ContextSourceRepository.get_by_id(
            session=session, source_id=source_id
        )
        assert fetched is not None
        assert fetched.label == "My GitHub"
        assert fetched.url == "https://github.com/octocat"
        assert fetched.description == "octocat profile"
        assert fetched.kind == ContextSourceKind.GITHUB


async def test_get_by_id_returns_none_when_missing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        assert (
            await ContextSourceRepository.get_by_id(session=session, source_id=999)
            is None
        )


async def test_list_all_returns_every_source(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        first = await ContextSourceRepository.create(
            session=session,
            label="First",
            url="https://example.com/1",
            description=None,
            kind=ContextSourceKind.WEB,
        )
        second = await ContextSourceRepository.create(
            session=session,
            label="Second",
            url="https://example.com/2",
            description=None,
            kind=ContextSourceKind.WEB,
        )

        result = await ContextSourceRepository.list_all(session=session)
        assert {s.id for s in result} == {first.id, second.id}


async def test_list_ok_filters_out_non_ok_sources(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        pending = await ContextSourceRepository.create(
            session=session,
            label="Pending",
            url="https://example.com/pending",
            description=None,
            kind=ContextSourceKind.WEB,
        )
        ok = await ContextSourceRepository.create(
            session=session,
            label="OK",
            url="https://example.com/ok",
            description=None,
            kind=ContextSourceKind.WEB,
        )
        await ContextSourceRepository.set_snapshot(
            session=session,
            source_id=ok.id,
            content="fetched content",
            status=ContextSourceStatus.OK,
            error=None,
        )

        result = await ContextSourceRepository.list_ok(session=session)
        ids = [s.id for s in result]
        assert ids == [ok.id]
        assert pending.id not in ids


async def test_set_snapshot_writes_content_status_and_fetched_at(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        created = await ContextSourceRepository.create(
            session=session,
            label="Site",
            url="https://example.com",
            description=None,
            kind=ContextSourceKind.WEB,
        )
        source_id = created.id

    async with session_factory() as session:
        updated = await ContextSourceRepository.set_snapshot(
            session=session,
            source_id=source_id,
            content="page text",
            status=ContextSourceStatus.OK,
            error=None,
        )
        assert updated is not None
        assert updated.content == "page text"
        assert updated.status == ContextSourceStatus.OK
        assert updated.error is None
        assert updated.fetched_at is not None
        assert isinstance(updated.fetched_at, datetime)


async def test_set_snapshot_records_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        created = await ContextSourceRepository.create(
            session=session,
            label="Site",
            url="https://example.com",
            description=None,
            kind=ContextSourceKind.WEB,
        )
        source_id = created.id

    async with session_factory() as session:
        updated = await ContextSourceRepository.set_snapshot(
            session=session,
            source_id=source_id,
            content=None,
            status=ContextSourceStatus.ERROR,
            error="timeout",
        )
        assert updated is not None
        assert updated.status == ContextSourceStatus.ERROR
        assert updated.error == "timeout"
        assert updated.fetched_at is not None


async def test_set_snapshot_returns_none_when_missing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        result = await ContextSourceRepository.set_snapshot(
            session=session,
            source_id=999,
            content="x",
            status=ContextSourceStatus.OK,
            error=None,
        )
        assert result is None


async def test_update_fields_mutates_label_url_description(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        created = await ContextSourceRepository.create(
            session=session,
            label="Old label",
            url="https://old.example.com",
            description="old desc",
            kind=ContextSourceKind.WEB,
        )
        source_id = created.id

    async with session_factory() as session:
        updated = await ContextSourceRepository.update_fields(
            session=session,
            source_id=source_id,
            label="New label",
            url="https://new.example.com",
            description="new desc",
        )
        assert updated is not None
        assert updated.label == "New label"
        assert updated.url == "https://new.example.com"
        assert updated.description == "new desc"


async def test_update_fields_returns_none_when_missing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        result = await ContextSourceRepository.update_fields(
            session=session,
            source_id=999,
            label="X",
            url="https://x.example.com",
            description=None,
        )
        assert result is None


async def test_delete_removes_source_and_returns_true(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        created = await ContextSourceRepository.create(
            session=session,
            label="To delete",
            url="https://example.com/delete",
            description=None,
            kind=ContextSourceKind.WEB,
        )
        source_id = created.id

    async with session_factory() as session:
        assert (
            await ContextSourceRepository.delete(session=session, source_id=source_id)
            is True
        )
        assert (
            await ContextSourceRepository.get_by_id(
                session=session, source_id=source_id
            )
            is None
        )


async def test_delete_returns_false_when_missing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        assert (
            await ContextSourceRepository.delete(session=session, source_id=999)
            is False
        )
