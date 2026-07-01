from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from headhunter_backend.db.models import CoverLetterORM


class CoverLetterRepository:
    @classmethod
    async def create(
        cls, session: AsyncSession, application_id: int, text: str
    ) -> CoverLetterORM:
        latest = await cls.get_latest_by_application_id(
            session=session, application_id=application_id
        )
        version = 1 if latest is None else latest.version + 1
        cover_letter = CoverLetterORM(
            application_id=application_id, text=text, version=version
        )
        session.add(cover_letter)
        await session.commit()
        return cover_letter

    @classmethod
    async def get_latest_by_application_id(
        cls, session: AsyncSession, application_id: int
    ) -> CoverLetterORM | None:
        stmt = (
            select(CoverLetterORM)
            .where(CoverLetterORM.application_id == application_id)
            .order_by(CoverLetterORM.version.desc())
            .limit(1)
        )
        result = await session.execute(statement=stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def list_by_application_id(
        cls, session: AsyncSession, application_id: int
    ) -> Sequence[CoverLetterORM]:
        result = await session.execute(
            select(CoverLetterORM).where(
                CoverLetterORM.application_id == application_id
            )
        )
        return result.scalars().all()
