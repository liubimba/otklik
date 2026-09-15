from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.api.schemas import ProcessingState
from otklik_backend.db.models import (
    ApplicationORM,
    RateLimitEventORM,
)
from otklik_backend.db.repositories.settings import SettingsRepository

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def _window_free_at(
    clock: datetime, events: list[datetime], window: timedelta, limit: int
) -> datetime:
    in_window = sorted(event for event in events if event > clock - window)
    if len(in_window) < limit:
        return clock
    binding = in_window[len(in_window) - limit]
    return binding + window


def project_schedule(
    now: datetime,
    past_events: list[datetime],
    queued_vacancy_ids: list[int],
    hourly_limit: int,
    daily_limit: int,
    pacing_seconds: float,
) -> dict[int, datetime]:
    events = sorted(event for event in past_events if event > now - DAY)
    clock = now
    schedule: dict[int, datetime] = {}
    for vacancy_id in queued_vacancy_ids:
        slot = max(
            clock,
            _window_free_at(clock, events, HOUR, hourly_limit),
            _window_free_at(clock, events, DAY, daily_limit),
        )
        schedule[vacancy_id] = slot
        events.append(slot)
        clock = slot + timedelta(seconds=pacing_seconds)
    return schedule


async def scheduled_send_times(session: AsyncSession) -> dict[int, datetime]:
    settings = await SettingsRepository.get(session=session)
    now = datetime.now()

    events_result = await session.execute(
        select(RateLimitEventORM.occurred_at).where(
            RateLimitEventORM.occurred_at > now - DAY
        )
    )
    past_events = [row[0] for row in events_result.all()]

    queued_result = await session.execute(
        select(ApplicationORM.vacancy_id)
        .where(ApplicationORM.status == ProcessingState.LETTER_QUEUED)
        .order_by(ApplicationORM.updated_at.asc().nulls_last(), ApplicationORM.id.asc())
    )
    queued_vacancy_ids = [row[0] for row in queued_result.all()]

    return project_schedule(
        now=now,
        past_events=past_events,
        queued_vacancy_ids=queued_vacancy_ids,
        hourly_limit=settings.hourly_limit,
        daily_limit=settings.daily_limit,
        pacing_seconds=settings.min_delay_ms / 1000.0,
    )
