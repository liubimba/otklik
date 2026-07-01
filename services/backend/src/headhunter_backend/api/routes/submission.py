from fastapi import APIRouter, HTTPException, status
from statemachine.exceptions import TransitionNotAllowed

from headhunter_backend.api.dependencies import (
    SessionDep,
    StateServiceDep,
)
from headhunter_backend.api.schemas import ApplicationAPISchema
from headhunter_backend.db.converters import application_to_schema
from headhunter_backend.db.models import ApplicationORM, VacancyORM
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator.state_machine import ApplicationEvent

submission_router = APIRouter(prefix="/vacancies", tags=["vacancies"])
log = get_logger(__name__)


@submission_router.post(
    "/{vacancy_id}/submit", status_code=status.HTTP_200_OK, summary="Submit vacancy"
)
async def submit(
    vacancy_id: int,
    session: SessionDep,
    state_service: StateServiceDep,
) -> ApplicationAPISchema:
    vacancy: VacancyORM | None = await VacancyRepository.get_by_id(
        session=session, vacancy_id=vacancy_id
    )
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    application: ApplicationORM | None = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(
            status_code=409, detail="Vacancy is not queued for a cover letter"
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
            detail=f"Unavailable state for to submit cover letter. Error: {e}",
        )
    # LetterSendingWorker self-enqueues on the ApplicationWSEvent published
    # by state_service.transition — no explicit enqueue here.
    return application_to_schema(orm=application)


@submission_router.post("/{vacancy_id}/skip")
async def skip(
    session: SessionDep, vacancy_id: int, state_service: StateServiceDep
) -> ApplicationAPISchema:
    vacancy: VacancyORM | None = await VacancyRepository.get_by_id(
        session=session, vacancy_id=vacancy_id
    )
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    application: ApplicationORM | None = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=409, detail="Vacancy not queued for letter")
    try:
        application = await state_service.transition(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.SKIP,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409, detail=f"Unavailable state to skip letter. Error: {e}"
        )
    return application_to_schema(orm=application)
