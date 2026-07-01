from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from headhunter_backend.api.schemas import RateLimitsBudgetAPISchema
from headhunter_backend.db.repositories.rate_limits import RateLimitRepository


def test_budget_empty(client) -> None:
    response = client.get("/api/v1/system/rate-limits")
    assert response.status_code == 200
    payload = RateLimitsBudgetAPISchema.model_validate(response.json())
    assert payload.hourly.used == 0
    assert payload.daily.used == 0
    # defaults from SettingsAPISchema()
    assert payload.hourly.limit == 5
    assert payload.daily.limit == 30


async def test_budget_counts_submissions(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session:
        await RateLimitRepository.log_submission(session=session)
        await RateLimitRepository.log_submission(session=session)
        await RateLimitRepository.log_submission(session=session)

    response = client.get("/api/v1/system/rate-limits")
    payload = RateLimitsBudgetAPISchema.model_validate(response.json())
    assert payload.hourly.used == 3
    assert payload.daily.used == 3


def test_budget_resets_at_is_returned(client) -> None:
    response = client.get("/api/v1/system/rate-limits")
    payload = RateLimitsBudgetAPISchema.model_validate(response.json())
    assert payload.hourly.resets_at is not None
    assert payload.daily.resets_at is not None
    assert payload.daily.resets_at > payload.hourly.resets_at
