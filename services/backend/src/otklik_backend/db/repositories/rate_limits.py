from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.db.models import RateLimitEventORM
from otklik_backend.db.repositories.settings import SettingsRepository


class RateLimitExceeded(Exception):
    def __init__(self, window: str, current: int, limit: int) -> None:
        self.window = window
        self.current = current
        self.limit = limit
        super().__init__(f"Rate limit exceeded ({window}: {current}/{limit})")


class RateLimitRepository:
    @classmethod
    async def log_submission(cls, session: AsyncSession) -> None:
        session.add(RateLimitEventORM())
        await session.commit()

    @classmethod
    async def count_submissions_since(
        cls, session: AsyncSession, since: datetime
    ) -> int:
        stmt = select(func.count(RateLimitEventORM.id)).where(
            RateLimitEventORM.occurred_at > since
        )
        result = await session.execute(statement=stmt)
        return result.scalar_one()

    @classmethod
    async def ensure_within_limits(cls, session: AsyncSession) -> None:
        settings = await SettingsRepository.get(session=session)
        now = datetime.now()

        hourly = await cls.count_submissions_since(
            session=session, since=now - timedelta(hours=1)
        )
        if hourly >= settings.hourly_limit:
            raise RateLimitExceeded(
                window="hour", current=hourly, limit=settings.hourly_limit
            )

        daily = await cls.count_submissions_since(
            session=session, since=now - timedelta(days=1)
        )
        if daily >= settings.daily_limit:
            raise RateLimitExceeded(
                window="day", current=daily, limit=settings.daily_limit
            )
