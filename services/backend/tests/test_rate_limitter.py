import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from headhunter_backend.db.models import RateLimitEventORM
from headhunter_backend.db.repositories.rate_limits import (
    RateLimitExceeded,
    RateLimitRepository,
)
from headhunter_backend.db.repositories.settings import SettingsRepository


async def test_no_events_passes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await RateLimitRepository.ensure_within_limits(session=session)  # не падает


async def test_under_hourly_limit_passes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # default hourly_limit = 5 → 4 события безопасны
    async with session_factory() as session:
        for _ in range(4):
            await RateLimitRepository.log_submission(session=session)
        await RateLimitRepository.ensure_within_limits(session=session)


async def test_hourly_limit_exceeded_raises(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        for _ in range(5):
            await RateLimitRepository.log_submission(session=session)
        with pytest.raises(RateLimitExceeded) as exc:
            await RateLimitRepository.ensure_within_limits(session=session)
        assert exc.value.window == "hour"
        assert exc.value.limit == 5
        assert exc.value.current == 5


async def test_daily_limit_exceeded_raises(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        settings = await SettingsRepository.get(session=session)
        settings.hourly_limit = 999
        await session.commit()

        past = datetime.now() - timedelta(hours=2)
        for _ in range(30):
            session.add(RateLimitEventORM(occurred_at=past))
        await session.commit()

        with pytest.raises(RateLimitExceeded) as exc:
            await RateLimitRepository.ensure_within_limits(session=session)
        assert exc.value.window == "day"


async def test_count_submissions_since_filters_by_time(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(RateLimitEventORM(occurred_at=datetime.now() - timedelta(hours=2)))
        session.add(RateLimitEventORM())
        await session.commit()

        recent = await RateLimitRepository.count_submissions_since(
            session=session, since=datetime.now() - timedelta(minutes=1)
        )
        assert recent == 1

        all_time = await RateLimitRepository.count_submissions_since(
            session=session, since=datetime.now() - timedelta(days=10)
        )
        assert all_time == 2
