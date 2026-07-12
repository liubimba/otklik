from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.api.schemas import SearchStatusAPISchema
from otklik_backend.db.models import SearchHistoryORM


class SearchHistoryRepository:
    _UPDATABLE_COLUMNS = frozenset(
        {"status", "parsed_pages", "parsed_vacancies", "finished_at", "error"}
    )

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        search_id: str,
        url: str,
        max_vacancies: int,
        max_pages: int,
        search_status: SearchStatusAPISchema,
    ) -> SearchHistoryORM:
        search_history = SearchHistoryORM(
            id=search_id,
            url=url,
            max_vacancies=max_vacancies,
            max_pages=max_pages,
            status=search_status,
        )
        session.add(search_history)
        await session.commit()
        return search_history

    @classmethod
    async def list_all(cls, session: AsyncSession) -> Sequence[SearchHistoryORM]:
        result = await session.execute(
            select(SearchHistoryORM).order_by(SearchHistoryORM.started_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def get_latest_id(cls, session: AsyncSession) -> str | None:
        stmt = (
            select(SearchHistoryORM.id)
            .order_by(SearchHistoryORM.started_at.desc())
            .limit(1)
        )
        result = await session.execute(statement=stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        search_id: str,
        **kwargs: Any,
    ) -> SearchHistoryORM | None:
        row = await session.get(SearchHistoryORM, search_id)
        if row is None:
            return None
        for key, value in kwargs.items():
            if key not in cls._UPDATABLE_COLUMNS:
                raise ValueError(f"Cannot update column: {key}")
            setattr(row, key, value)
        await session.commit()
        return row
