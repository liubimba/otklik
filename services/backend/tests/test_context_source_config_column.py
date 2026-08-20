from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.core.context_source import ContextSourceKind
from otklik_backend.db.models import ContextSourceORM


async def test_config_column_stores_and_reads_back_json(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        source = ContextSourceORM(
            label="YouTrack project",
            url="https://yt.example",
            description=None,
            kind=ContextSourceKind.YOUTRACK,
            config={"base_url": "https://yt.example", "query": "for: me"},
        )
        session.add(source)
        await session.commit()
        source_id = source.id

    async with session_factory() as session:
        fetched = (
            await session.execute(
                select(ContextSourceORM).where(ContextSourceORM.id == source_id)
            )
        ).scalar_one()
        assert fetched.config == {
            "base_url": "https://yt.example",
            "query": "for: me",
        }


async def test_config_column_defaults_to_none(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        source = ContextSourceORM(
            label="GitHub profile",
            url="https://github.com/octocat",
            description=None,
            kind=ContextSourceKind.GITHUB,
        )
        session.add(source)
        await session.commit()
        source_id = source.id

    async with session_factory() as session:
        fetched = (
            await session.execute(
                select(ContextSourceORM).where(ContextSourceORM.id == source_id)
            )
        ).scalar_one()
        assert fetched.config is None
