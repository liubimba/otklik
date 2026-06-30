from fastapi import APIRouter, HTTPException, status

from statemachine.exceptions import TransitionNotAllowed

from headhunter_backend.api.dependencies import (
    BroadcasterDep,
    OrchestratorDep,
    SessionDep,
)
from headhunter_backend.api.schemas import ApplicationAPISchema
from headhunter_backend.db.converters import application_to_schema
from headhunter_backend.db.crud import get_application_by_vacancy_id, get_vacancy
from headhunter_backend.db.models import ApplicationORM, VacancyORM
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator._transitions import transition_and_broadcast
from headhunter_backend.orchestrator.state_machine import ApplicationEvent

submission_router = APIRouter(prefix="/vacancies", tags=["vacancies"])
log = get_logger(__name__)


@submission_router.post(
    "/{vacancy_id}/submit", status_code=status.HTTP_200_OK, summary="Submit vacancy"
)
async def submit(
    vacancy_id: int,
    session: SessionDep,
    orchestrator: OrchestratorDep,
    broadcaster: BroadcasterDep,
) -> ApplicationAPISchema:
    vacancy: VacancyORM | None = await get_vacancy(
        session=session, vacancy_id=vacancy_id
    )
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    application: ApplicationORM | None = await get_application_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(
            status_code=409, detail="Vacancy is not queued for a cover letter"
        )
    try:
        application = await transition_and_broadcast(
            session=session,
            broadcaster=broadcaster,
            application_id=application.id,
            to_state=ApplicationEvent.SUBMIT,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409,
            detail=f"Unavailable state for to submit cover letter. Error: {e}",
        )
    await orchestrator.enqueue(application_id=application.id)
    return application_to_schema(orm=application)


@submission_router.post("/{vacancy_id}/skip")
async def skip(
    session: SessionDep, vacancy_id: int, broadcaster: BroadcasterDep
) -> ApplicationAPISchema:
    vacancy: VacancyORM | None = await get_vacancy(
        session=session, vacancy_id=vacancy_id
    )
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    application: ApplicationORM | None = await get_application_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=409, detail="Vacancy not queued for letter")
    try:
        application = await transition_and_broadcast(
            session=session,
            broadcaster=broadcaster,
            application_id=application.id,
            to_state=ApplicationEvent.SKIP,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409, detail=f"Unavailable state to skip letter. Error: {e}"
        )
    return application_to_schema(orm=application)
