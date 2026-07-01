from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from headhunter_backend.api.schemas import (
    RateLimitInfoAPISchema,
    SettingsAPISchema,
)
from headhunter_backend.db.converters import settings_to_schema
from headhunter_backend.db.repositories.rate_limits import RateLimitRepository
from headhunter_backend.db.repositories.settings import SettingsRepository


async def get_used_hourly_limits(session: AsyncSession) -> RateLimitInfoAPISchema:
    settings: SettingsAPISchema = settings_to_schema(
        orm=await SettingsRepository.get(session=session)
    )
    now = datetime.now()
    used = await RateLimitRepository.count_submissions_since(
        session=session, since=now - timedelta(hours=1)
    )
    return RateLimitInfoAPISchema(
        used=used,
        limit=settings.rate_limits.hourly_limit,
        resets_at=now + timedelta(hours=1),
    )


async def get_used_daily_limits(session: AsyncSession) -> RateLimitInfoAPISchema:
    settings: SettingsAPISchema = settings_to_schema(
        orm=await SettingsRepository.get(session=session)
    )
    now = datetime.now()
    used = await RateLimitRepository.count_submissions_since(
        session=session, since=now - timedelta(days=1)
    )
    return RateLimitInfoAPISchema(
        used=used,
        limit=settings.rate_limits.daily_limit,
        resets_at=now + timedelta(days=1),
    )
