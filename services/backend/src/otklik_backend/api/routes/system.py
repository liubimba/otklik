from datetime import datetime, timedelta

from fastapi import APIRouter

from otklik_backend.ai.health import AILayerHealthStatus
from otklik_backend.api.dependencies import (
    AILayerDep,
    OrchestratorDep,
    SessionDep,
)
from otklik_backend.api.schemas import (
    AIHealthStatusAPISchema,
    OrchestratorStatusAPISchema,
    RateLimitInfoAPISchema,
    RateLimitsBudgetAPISchema,
    SettingsAPISchema,
)
from otklik_backend.db.converters import settings_to_schema
from otklik_backend.db.repositories.rate_limits import RateLimitRepository
from otklik_backend.db.repositories.settings import SettingsRepository

system_router = APIRouter(prefix="/system", tags=["system"])


@system_router.get("/rate-limits")
async def rate_limits(session: SessionDep) -> RateLimitsBudgetAPISchema:
    settings: SettingsAPISchema = settings_to_schema(
        orm=await SettingsRepository.get(session=session)
    )
    now = datetime.now()
    hourly_used = await RateLimitRepository.count_submissions_since(
        session=session, since=now - timedelta(hours=1)
    )
    daily_used = await RateLimitRepository.count_submissions_since(
        session=session, since=now - timedelta(days=1)
    )
    return RateLimitsBudgetAPISchema(
        hourly=RateLimitInfoAPISchema(
            used=hourly_used,
            limit=settings.rate_limits.hourly_limit,
            resets_at=now + timedelta(hours=1),
        ),
        daily=RateLimitInfoAPISchema(
            used=daily_used,
            limit=settings.rate_limits.daily_limit,
            resets_at=now + timedelta(days=1),
        ),
    )


@system_router.get("/ai/health")
async def ai_health(ai_layer: AILayerDep) -> AIHealthStatusAPISchema:
    status: AILayerHealthStatus = await ai_layer.get_health_status()
    return AIHealthStatusAPISchema(status=status.value)


@system_router.get("/orchestrator/status")
def orchestrator_status(orchestrator: OrchestratorDep) -> OrchestratorStatusAPISchema:
    return OrchestratorStatusAPISchema(
        reason=orchestrator.get_pause_reason(),
        paused=orchestrator.is_paused(),
        queue_size=orchestrator.qsize(),
        queue=orchestrator.get_application_ids(),
    )


@system_router.post("/orchestrator/resume")
def orchestrator_resume(orchestrator: OrchestratorDep) -> None:
    orchestrator.resume()
