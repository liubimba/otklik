from fastapi import APIRouter, HTTPException

from statemachine.exceptions import TransitionNotAllowed

from headhunter_backend.api.dependencies import BroadcasterDep, SessionDep
from headhunter_backend.api.events import ApplicationData, ApplicationWSEvent
from headhunter_backend.api.schemas import (
    ApplicationAPISchema,
    CoverLetterAPISchema,
    CoverLetterRequestAPISchema,
    ProcessingState,
)
from headhunter_backend.db.converters import application_to_schema
from headhunter_backend.db.crud import (
    create_application,
    create_cover_letter,
    get_application_by_vacancy_id,
    get_vacancy,
    transition_application,
)
from headhunter_backend.db.models import ApplicationORM, CoverLetterORM, VacancyORM
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator._transitions import transition_and_broadcast
from headhunter_backend.orchestrator.state_machine import ApplicationEvent

letter_router = APIRouter(prefix="/vacancies", tags=["vacancies"])
log = get_logger(__name__)


@letter_router.post("/{vacancy_id}/queue_for_letter")
async def queue_for_letter(
    vacancy_id: int, session: SessionDep, broadcaster: BroadcasterDep
) -> ApplicationAPISchema:
    if await get_vacancy(session=session, vacancy_id=vacancy_id) is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    application: ApplicationORM | None = await get_application_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is not None:
        raise HTTPException(
            status_code=409, detail="Vacancy is queued for letter already"
        )
    application = await create_application(session=session, vacancy_id=vacancy_id)
    try:
        application = await transition_and_broadcast(
            session=session,
            broadcaster=broadcaster,
            application_id=application.id,
            to_state=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409, detail=f"Unavailable state to queue letter. Error: {e}"
        )
    return application_to_schema(orm=application)


@letter_router.post("/{vacancy_id}/cover_letter")
async def post_cover_letter(
    vacancy_id: int,
    session: SessionDep,
    letter: CoverLetterRequestAPISchema,
    broadcaster: BroadcasterDep,
) -> CoverLetterAPISchema:
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
    if application.status == ProcessingState.LETTER_PENDING:
        try:
            application = await transition_application(
                session=session,
                application_id=application.id,
                to_state=ApplicationEvent.LETTER_GENERATED,
            )
        except TransitionNotAllowed as e:
            raise HTTPException(
                status_code=409,
                detail=f"Unavailable state for cover letter. Error: {e}",
            )
        if application is None:
            raise HTTPException(status_code=500, detail="Server error")
    elif application.status not in (
        ProcessingState.LETTER_READY,
        ProcessingState.LETTER_REVIEWING,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Unavailable state for cover letter: {application.status.value}",
        )
    cover_letter: CoverLetterORM = await create_cover_letter(
        session=session, application_id=application.id, text=letter.text
    )
    await broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=vacancy_id,
                application_id=application.id,
                status=application.status,
            )
        )
    )
    return CoverLetterAPISchema(
        text=cover_letter.text,
        version=cover_letter.version,
        created_at=cover_letter.created_at,
    )


@letter_router.post("/{vacancy_id}/review")
async def review(
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
            to_state=ApplicationEvent.SEND_FOR_REVIEW,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409, detail=f"Unavailable state to queue letter. Error: {e}"
        )
    return application_to_schema(orm=application)


@letter_router.post("/{vacancy_id}/retry")
async def retry(
    vacancy_id: int, session: SessionDep, broadcaster: BroadcasterDep
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
            to_state=ApplicationEvent.RETRY,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409,
            detail=f"Unavailable state for to submit cover letter. Error: {e}",
        )
    return application_to_schema(orm=application)
