from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from headhunter_backend.db.models import ChatMessageORM


class ChatMessageRepository:
    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        application_id: int,
        role: str,
        content: str,
        produced_version: int | None = None,
    ) -> ChatMessageORM:
        message = ChatMessageORM(
            application_id=application_id,
            role=role,
            content=content,
            produced_version=produced_version,
        )
        session.add(message)
        await session.commit()
        return message

    @classmethod
    async def list_by_application_id(
        cls, session: AsyncSession, application_id: int
    ) -> Sequence[ChatMessageORM]:
        stmt = (
            select(ChatMessageORM)
            .where(ChatMessageORM.application_id == application_id)
            .order_by(ChatMessageORM.id)
        )
        result = await session.execute(statement=stmt)
        return result.scalars().all()
