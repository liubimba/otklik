from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.core.context_source import ContextSourceKind, ContextSourceStatus
from otklik_backend.db.models import ContextSourceORM


class ContextSourceRepository:
    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        *,
        label: str,
        url: str,
        description: str | None,
        kind: ContextSourceKind,
    ) -> ContextSourceORM:
        source = ContextSourceORM(
            label=label, url=url, description=description, kind=kind
        )
        session.add(source)
        await session.commit()
        return source

    @classmethod
    async def get_by_id(
        cls, session: AsyncSession, source_id: int
    ) -> ContextSourceORM | None:
        return await session.get(ContextSourceORM, source_id)

    @classmethod
    async def list_all(cls, session: AsyncSession) -> Sequence[ContextSourceORM]:
        stmt = select(ContextSourceORM).order_by(ContextSourceORM.created_at)
        result = await session.execute(statement=stmt)
        return result.scalars().all()

    @classmethod
    async def list_ok(cls, session: AsyncSession) -> Sequence[ContextSourceORM]:
        stmt = (
            select(ContextSourceORM)
            .where(ContextSourceORM.status == ContextSourceStatus.OK)
            .order_by(ContextSourceORM.created_at)
        )
        result = await session.execute(statement=stmt)
        return result.scalars().all()

    @classmethod
    async def set_snapshot(
        cls,
        session: AsyncSession,
        source_id: int,
        *,
        content: str | None,
        status: ContextSourceStatus,
        error: str | None,
    ) -> ContextSourceORM | None:
        source = await cls.get_by_id(session=session, source_id=source_id)
        if source is None:
            return None
        source.content = content
        source.status = status
        source.error = error
        source.fetched_at = datetime.now()
        await session.commit()
        return source

    @classmethod
    async def update_fields(
        cls,
        session: AsyncSession,
        source_id: int,
        *,
        label: str,
        url: str,
        description: str | None,
    ) -> ContextSourceORM | None:
        source = await cls.get_by_id(session=session, source_id=source_id)
        if source is None:
            return None
        source.label = label
        source.url = url
        source.description = description
        await session.commit()
        return source

    @classmethod
    async def delete(cls, session: AsyncSession, source_id: int) -> bool:
        source = await cls.get_by_id(session=session, source_id=source_id)
        if source is None:
            return False
        await session.delete(source)
        await session.commit()
        return True
