from fastapi import APIRouter
from headhunter_backend.api.dependencies import SessionDep
from headhunter_backend.api.schemas import RateLimitsBudgetAPISchema
from headhunter_backend.orchestrator.rate_limiter import (
    get_used_daily_limits,
    get_used_hourly_limits,
)

rate_limits_router = APIRouter(prefix="/rate-limits", tags=["rate-limits"])


@rate_limits_router.get("/budget")
async def get_rate_limits(session: SessionDep) -> RateLimitsBudgetAPISchema:
    return RateLimitsBudgetAPISchema(
        hourly=await get_used_hourly_limits(session=session),
        daily=await get_used_daily_limits(session=session),
    )
