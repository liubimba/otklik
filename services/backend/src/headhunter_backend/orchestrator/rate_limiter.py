from headhunter_backend.api.schemas import SettingsAPISchema
from sqlalchemy.ext.asyncio import AsyncSession
from headhunter_backend.db.crud import get_settings, count_submissions_since
from headhunter_backend.db.converters import settings_to_schema
from datetime import datetime, timedelta


class RateLimitExceeded(Exception):
    def __init__(self, window: str, current: int, limit: int) -> None:
        self.window = window
        self.current = current
        self.limit = limit
        super().__init__(f"Rate limit exceeded ({window}: {current}/{limit})")


async def ensure_within_limits(session: AsyncSession) -> None:
    settings: SettingsAPISchema = settings_to_schema(
        orm=await get_settings(session=session)
    )
    now: datetime = datetime.now()

    hourly = await count_submissions_since(
        session=session, since=now - timedelta(hours=1)
    )

    if hourly >= settings.rate_limits.hourly_limit:
        raise RateLimitExceeded(
            window="hour", current=hourly, limit=settings.rate_limits.hourly_limit
        )

    daily = await count_submissions_since(
        session=session, since=now - timedelta(days=1)
    )

    if daily >= settings.rate_limits.daily_limit:
        raise RateLimitExceeded(
            window="day", current=daily, limit=settings.rate_limits.daily_limit
        )
