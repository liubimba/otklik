from typing import Sequence

from fastapi import APIRouter, HTTPException, status
from statemachine.exceptions import TransitionNotAllowed

from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.api.dependencies import (
    CoverLetterServiceDep,
    SessionDep,
    StateServiceDep,
)
from headhunter_backend.api.schemas import (
    AICoverLetterAPISchema,
    ApplicationDetailAPISchema,
    CoverLetterAPISchema,
    CoverLetterRequestAPISchema,
    SubmitApplicationRequestAPISchema,
)
from headhunter_backend.db.models import ApplicationORM, CoverLetterORM, VacancyORM
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator.state_machine import ApplicationEvent

application_router = APIRouter(
    prefix="/vacancies/{vacancy_id}/application", tags=["application"]
)
log = get_logger(__name__)


async def _load_or_404(session, vacancy_id: int) -> VacancyORM:
    vacancy = await VacancyRepository.get_by_id(session=session, vacancy_id=vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


async def _build_detail(
    session, application: ApplicationORM
) -> ApplicationDetailAPISchema:
    letters: Sequence[
        CoverLetterORM
    ] = await CoverLetterRepository.list_by_application_id(
        session=session, application_id=application.id
    )
    latest = max(letters, key=lambda letter: letter.version, default=None)
    return ApplicationDetailAPISchema(
        vacancy_id=application.vacancy_id,
        application_id=application.id,
        retry_count=application.retry_count,
        status=application.status,
        reason=application.error_message,
        created_at=application.created_at,
        updated_at=application.updated_at,
        latest_letter=CoverLetterAPISchema(
            text=latest.text, version=latest.version, created_at=latest.created_at
        )
        if latest is not None
        else None,
        letters_count=len(letters),
    )


@application_router.get("")
async def get_application(
    vacancy_id: int, session: SessionDep
) -> ApplicationDetailAPISchema:
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return await _build_detail(session=session, application=application)


@application_router.get("/letters")
async def get_letters(
    vacancy_id: int, session: SessionDep
) -> Sequence[CoverLetterAPISchema]:
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    letters = await CoverLetterRepository.list_by_application_id(
        session=session, application_id=application.id
    )
    return [
        CoverLetterAPISchema(
            text=letter.text, version=letter.version, created_at=letter.created_at
        )
        for letter in letters
    ]


@application_router.post("/generate")
async def generate(
    vacancy_id: int,
    session: SessionDep,
    state_service: StateServiceDep,
    cover_letter_service: CoverLetterServiceDep,
) -> AICoverLetterAPISchema:
    """One-shot generation. If no Application exists, creates it and transitions
    PARSED → LETTER_PENDING before running the LLM. The client does not need to
    call `queue_for_letter` first."""
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        application = await ApplicationRepository.create(
            session=session, vacancy_id=vacancy_id
        )
        try:
            await state_service.transition(
                session=session,
                application_id=application.id,
                event=ApplicationEvent.ENQUEUE_FOR_LETTER,
            )
        except TransitionNotAllowed as e:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot enqueue for letter: {e}",
            )
    result: AICoverLetterResult = await cover_letter_service.regenerate(
        vacancy_id=vacancy_id
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


@application_router.post("/save")
async def save(
    vacancy_id: int,
    letter: CoverLetterRequestAPISchema,
    session: SessionDep,
) -> CoverLetterAPISchema:
    """Save a draft version of the letter. Pure content write — does NOT drive
    the state machine (unlike the removed POST /cover_letter which secretly
    transitioned LETTER_PENDING → LETTER_GENERATED)."""
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(
            status_code=409, detail="Application does not exist for this vacancy"
        )
    created = await CoverLetterRepository.create(
        session=session, application_id=application.id, text=letter.text
    )
    return CoverLetterAPISchema(
        text=created.text, version=created.version, created_at=created.created_at
    )


@application_router.post("/submit", status_code=status.HTTP_200_OK)
async def submit(
    vacancy_id: int,
    body: SubmitApplicationRequestAPISchema,
    session: SessionDep,
    state_service: StateServiceDep,
) -> ApplicationDetailAPISchema:
    """Submit the application to hh.ru. If `text` is provided, saves it as a
    new letter version first (atomic dirty-submit)."""
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(
            status_code=409, detail="Application does not exist for this vacancy"
        )
    if body.text is not None:
        await CoverLetterRepository.create(
            session=session, application_id=application.id, text=body.text
        )
    try:
        application = await state_service.transition(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.SUBMIT,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot submit application: {e}",
        )
    return await _build_detail(session=session, application=application)


@application_router.post("/skip")
async def skip(
    vacancy_id: int, session: SessionDep, state_service: StateServiceDep
) -> ApplicationDetailAPISchema:
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=409, detail="Application does not exist")
    try:
        application = await state_service.transition(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.SKIP,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(status_code=409, detail=f"Cannot skip: {e}")
    return await _build_detail(session=session, application=application)


@application_router.post("/retry")
async def retry(
    vacancy_id: int, session: SessionDep, state_service: StateServiceDep
) -> ApplicationDetailAPISchema:
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=409, detail="Application does not exist")
    try:
        application = await state_service.transition(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.RETRY,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(status_code=409, detail=f"Cannot retry: {e}")
    return await _build_detail(session=session, application=application)
