from fastapi import APIRouter, HTTPException
from headhunter_backend.api.dependencies import SessionDep, AILayerDep
from headhunter_backend.db.crud import (
    get_vacancy,
    get_settings,
    get_application_by_vacancy_id,
)
from headhunter_backend.db.models import VacancyORM, SettingsORM, ApplicationORM
from headhunter_backend.db.converters import vacancy_to_model
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.api.schemas import (
    AICoverLetterResponseAPISchema,
    AIHealthStatusAPISchema,
)
from headhunter_backend.ai.health import AILayerHealthStatus

ai_router = APIRouter(prefix="/ai", tags=["ai"])


@ai_router.post("/create_cover_letter/{vacancy_id}")
async def generate_cover_letter(
    session: SessionDep, ai_layer: AILayerDep, vacancy_id: int
) -> AICoverLetterResponseAPISchema:
    if not (await ai_layer.get_health_status()).is_ready():
        raise HTTPException(
            status_code=409, detail="AILayer is not ready to generate cover letter"
        )
    vacancy_orm: VacancyORM | None = await get_vacancy(
        session=session, vacancy_id=vacancy_id
    )
    if vacancy_orm is None:
        raise HTTPException(status_code=404, detail="vacancy not found")
    application_orm: ApplicationORM | None = await get_application_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application_orm is None:
        raise HTTPException(
            status_code=409, detail="vacancy was not queue for cover letter"
        )
    settings_orm: SettingsORM = await get_settings(session=session)
    cover_letter: AICoverLetterResult = await ai_layer.generate_cover_letter(
        vacancy_model=vacancy_to_model(row=vacancy_orm),
        resume=settings_orm.resume_text,
        style=settings_orm.letter_style,
        system_prompt=settings_orm.llm_system_prompt,
    )
    return AICoverLetterResponseAPISchema(
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
