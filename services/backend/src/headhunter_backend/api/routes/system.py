from fastapi import APIRouter

from headhunter_backend.ai.health import AILayerHealthStatus
from headhunter_backend.api.dependencies import AILayerDep, OrchestratorDep, SessionDep
from headhunter_backend.api.schemas import (
    AIHealthStatusAPISchema,
    OrchestratorStatusAPISchema,
    RateLimitsBudgetAPISchema,
)
from headhunter_backend.orchestrator.rate_limiter import (
    get_used_daily_limits,
    get_used_hourly_limits,
)

system_router = APIRouter(prefix="/system", tags=["system"])


@system_router.get("/rate-limits")
async def rate_limits(session: SessionDep) -> RateLimitsBudgetAPISchema:
    return RateLimitsBudgetAPISchema(
        hourly=await get_used_hourly_limits(session=session),
        daily=await get_used_daily_limits(session=session),
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
