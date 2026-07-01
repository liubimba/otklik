from fastapi import APIRouter
from headhunter_backend.api.dependencies import (
    SessionDep,
    AILayerDep,
    CoverLetterServiceDep,
)
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.api.schemas import (
    AICoverLetterAPISchema,
    AIHealthStatusAPISchema,
)
from headhunter_backend.ai.health import AILayerHealthStatus

ai_router = APIRouter(prefix="/ai", tags=["ai"])


@ai_router.post("/create_cover_letter/{vacancy_id}")
async def generate_cover_letter(
    session: SessionDep,
    ai_layer: AILayerDep,
    vacancy_id: int,
    cover_letter_service: CoverLetterServiceDep,
) -> AICoverLetterAPISchema:
    cover_letter: AICoverLetterResult = await cover_letter_service.regenerate(
        vacancy_id=vacancy_id
    )
    return AICoverLetterAPISchema(
        text=cover_letter.text,
        model_used=cover_letter.model_used,
        prompt_tokens=cover_letter.prompt_tokens,
        completion_tokens=cover_letter.completion_tokens,
        total_tokens=cover_letter.total_tokens,
        was_fallback=cover_letter.was_fallback,
        cost_usd=cover_letter.cost_usd,
    )


@ai_router.get("/health")
async def health(ai_layer: AILayerDep) -> AIHealthStatusAPISchema:
    health: AILayerHealthStatus = await ai_layer.get_health_status()
    return AIHealthStatusAPISchema(status=health.value)
