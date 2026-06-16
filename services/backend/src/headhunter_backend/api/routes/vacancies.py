from fastapi import APIRouter, HTTPException, Query, status
from headhunter_backend.api.schemas import (
    ApplicationAPISchema,
    CoverLetterRequestAPISchema,
    CoverLetterAPISchema,
    ProcessingState,
    VacancyAPISchema,
)
from headhunter_backend.db.models import (
    VacancyORM,
    ApplicationORM,
    CoverLetterORM,
)
from headhunter_backend.db.converters import (
    vacancy_to_schema,
    application_to_schema,
    cover_letter_to_schema,
)
from headhunter_backend.db.crud import (
    list_vacancies,
    get_vacancy,
    get_application_by_vacancy_id,
    create_cover_letter,
    transition_application,
    create_application,
    get_latest_search_id,
    get_latest_cover_letter,
    list_cover_letters_by_application_id,
)
from headhunter_backend.api.dependencies import (
    SessionDep,
    OrchestratorDep,
    BroadcasterDep,
)
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from statemachine.exceptions import TransitionNotAllowed
from headhunter_backend.log import get_logger
from typing import Sequence
from headhunter_backend.api.events import ApplicationWSEvent, ApplicationData

vacancies_router = APIRouter(prefix="/vacancies", tags=["vacancies"])
log = get_logger(__name__)


@vacancies_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="List vacancies (default: current/latest search)",
)
async def find_all(
    session: SessionDep,
    search_id: str = Query(
        default="latest",
        description='Search filter: "latest" (current/most recent search), "all" (no filter), or a search UUID.',
    ),
) -> Sequence[VacancyAPISchema]:
    if search_id == "all":
        rows: Sequence[VacancyORM] = await list_vacancies(session=session)
    elif search_id == "latest":
        latest: str | None = await get_latest_search_id(session=session)
        if latest is None:
            return []
        rows = await list_vacancies(session=session, search_id=latest)
    else:
        rows = await list_vacancies(session=session, search_id=search_id)
    return [vacancy_to_schema(row=row) for row in rows]


@vacancies_router.get(
    "/{vacancy_id}", status_code=status.HTTP_200_OK, summary="Find vacancy by ID"
)
async def find_by_id(vacancy_id: int, session: SessionDep) -> VacancyAPISchema:
    result: VacancyORM | None = await get_vacancy(
        session=session, vacancy_id=vacancy_id
    )
    if result is not None:
        return vacancy_to_schema(row=result)
    raise HTTPException(status_code=404, detail="Vacancy not found")


@vacancies_router.post("/{vacancy_id}/review")
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
        application = await transition_application(
            session=session,
            application_id=application.id,
            to_state=ApplicationEvent.SEND_FOR_REVIEW,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409, detail=f"Unavailable state to queue letter. Error: {e}"
        )
    if application is None:
        raise HTTPException(status_code=500, detail="Server error")
    await broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=vacancy_id,
                application_id=application.id,
                status=application.status,
            )
        )
    )
    return application_to_schema(orm=application)


@vacancies_router.post("/{vacancy_id}/skip")
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
        application = await transition_application(
            session=session,
            application_id=application.id,
            to_state=ApplicationEvent.SKIP,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409, detail=f"Unavailable state to skip letter. Error: {e}"
        )
    if application is None:
        raise HTTPException(status_code=500, detail="Server error")
    await broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=vacancy_id,
                application_id=application.id,
                status=application.status,
            )
        )
    )
    return application_to_schema(orm=application)


@vacancies_router.post(
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
        application = await transition_application(
            session=session,
            application_id=application.id,
            to_state=ApplicationEvent.SUBMIT,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409,
            detail=f"Unavailable state for to submit cover letter. Error: {e}",
        )
    if application is None:
        raise HTTPException(status_code=500, detail="Server error")
    await orchestrator.enqueue(application_id=application.id)
    await broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=vacancy_id,
                application_id=application.id,
                status=application.status,
            )
        )
    )
    return application_to_schema(orm=application)


@vacancies_router.get("/{vacancy_id}/status")
async def get_status(vacancy_id: int, session: SessionDep) -> ApplicationAPISchema:
    application: ApplicationORM | None = await get_application_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return application_to_schema(orm=application)


@vacancies_router.post("/{vacancy_id}/queue_for_letter")
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
        application = await transition_application(
            session=session,
            application_id=application.id,
            to_state=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409, detail=f"Unavailable state to queue letter. Error: {e}"
        )
    if application is None:
        raise HTTPException(status_code=500, detail="Server error")
    await broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=vacancy_id,
                application_id=application.id,
                status=application.status,
            )
        )
    )
    return application_to_schema(orm=application)


@vacancies_router.get("/{vacancy_id}/cover_letter")
async def get_cover_letter(
    vacancy_id: int, session: SessionDep
) -> CoverLetterAPISchema:
    application: ApplicationORM | None = await get_application_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    cover_letter: CoverLetterORM | None = await get_latest_cover_letter(
        session=session, application_id=application.id
    )
    if cover_letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return CoverLetterAPISchema(
        text=cover_letter.text,
        version=cover_letter.version,
        created_at=cover_letter.created_at,
    )


@vacancies_router.get("/{vacancy_id}/cover_letters")
async def list_cover_letters(
    vacancy_id: int, session: SessionDep
) -> Sequence[CoverLetterAPISchema]:
    application: ApplicationORM | None = await get_application_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    cover_letters: Sequence[
        CoverLetterORM
    ] = await list_cover_letters_by_application_id(
        session=session, application_id=application.id
    )
    return list(map(lambda item: cover_letter_to_schema(orm=item), cover_letters))


@vacancies_router.post("/{vacancy_id}/cover_letter")
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


@vacancies_router.post("/{vacancy_id}/retry")
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
        application = await transition_application(
            session=session,
            application_id=application.id,
            to_state=ApplicationEvent.RETRY,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409,
            detail=f"Unavailable state for to submit cover letter. Error: {e}",
        )
    if application is None:
        raise HTTPException(status_code=500, detail="Server error")
    await broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=vacancy_id,
                application_id=application.id,
                status=application.status,
            )
        )
    )
    return application_to_schema(orm=application)
