from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from otklik_backend.core.context_source import ContextSourceKind, ContextSourceStatus
from otklik_backend.db.models import ContextSourceORM


async def test_created_source_defaults_to_pending_with_no_content(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        source = ContextSourceORM(
            label="My GitHub",
            url="https://github.com/octocat",
            kind=ContextSourceKind.GITHUB,
        )
        session.add(source)
        await session.commit()

        stored = (
            await session.execute(
                select(ContextSourceORM).where(ContextSourceORM.label == "My GitHub")
            )
        ).scalar_one()

        assert stored.status == ContextSourceStatus.PENDING
        assert stored.content is None
        assert stored.error is None
        assert stored.fetched_at is None
        assert stored.description is None
        assert stored.created_at is not None
