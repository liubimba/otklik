from fastapi import APIRouter

from otklik_backend.api.dependencies import (
    AILayerDep,
    ContextSourceServiceDep,
    SessionDep,
)
from otklik_backend.api.schemas import (
    AICoverLetterAPISchema,
    PreviewCoverLetterRequestAPISchema,
    VacancyAPISchema,
)
from otklik_backend.db.repositories.settings import SettingsRepository

ai_router: APIRouter = APIRouter(prefix="/ai", tags=["ai"])


@ai_router.post("/preview_cover_letter")
async def preview_cover_letter(
    body: PreviewCoverLetterRequestAPISchema,
    session: SessionDep,
    ai_layer: AILayerDep,
    context_sources: ContextSourceServiceDep,
) -> AICoverLetterAPISchema:
    settings = await SettingsRepository.get(session=session)
    sources = await context_sources.list_ok_for_llm()
    vacancy_model = VacancyAPISchema(
        title=body.title,
        apply_link="preview://local",
        description=body.description,
        company_name=body.company_name,
        salary=body.salary,
        work_location=body.work_location,
        work_formats=body.work_formats,
        employment_types=body.employment_types,
        work_experience=body.work_experience,
    )
    result = await ai_layer.generate_cover_letter(
        vacancy_model=vacancy_model,
        resume=settings.resume_text,
        style=settings.letter_style,
        system_prompt=settings.llm_system_prompt,
        sources=sources,
    )
    return AICoverLetterAPISchema(
        text=result.text,
        model_used=result.model_used,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        was_fallback=result.was_fallback,
        cost_usd=result.cost_usd,
    )
