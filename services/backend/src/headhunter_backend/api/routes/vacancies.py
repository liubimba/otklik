from fastapi import APIRouter, HTTPException, status
from headhunter_backend.api.schemas import (
    SearchRequestAPISchema,
    SearchResponseAPISchema,
    ApplicationStatusResponseAPISchema,
    CoverLetterRequest,
)
from headhunter_backend.domain.models import VacancyModel, SearchHistoryModel
from headhunter_backend.db.models import VacancyORM, ApplicationORM, SearchHistoryORM
from headhunter_backend.db.converters import vacancy_to_model, search_history_to_model
from headhunter_backend.db.crud import (
    list_vacancies,
    get_vacancy,
    get_application_by_vacancy_id,
    create_cover_letter,
    transition_application,
    create_application,
    list_search_history,
)
from headhunter_backend.api.dependencies import (
    SessionDep,
    OrchestratorDep,
    SearchServiceDep,
)
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from statemachine.exceptions import TransitionNotAllowed
from headhunter_backend.log import get_logger
from typing import Sequence
from headhunter_backend.orchestrator.search import SearchAlreadyRunning, SearchTask

vacancies_router = APIRouter(prefix="/vacancies", tags=["vacancies"])
log = get_logger(__name__)


@vacancies_router.get(
    "/", status_code=status.HTTP_200_OK, summary="Find all searched vacancies"
)
async def find_all(session: SessionDep) -> Sequence[VacancyModel]:
    result: Sequence[VacancyORM] = await list_vacancies(session=session)
    return list(map(lambda orm: vacancy_to_model(row=orm), result))


@vacancies_router.post(
    "/search", status_code=status.HTTP_200_OK, summary="Search vacancies by query"
)
async def search(
    filter: SearchRequestAPISchema, search_service: SearchServiceDep
) -> SearchResponseAPISchema:
    try:
        search_task: SearchTask = search_service.start_search(request=filter)
        return SearchResponseAPISchema(
            search_id=search_task.id,
            parsed_pages=search_task.parsed_pages,
            parsed_vacancies=search_task.parsed_count,
            status=search_task.state_machine.current_state_value,
        )
    except SearchAlreadyRunning:
        raise HTTPException(
            status_code=409,
            detail="another search is running, wait until it`s done or cancel it",
        )


@vacancies_router.get("/search/{search_id}")
async def find_search(
    search_id: str, search_service: SearchServiceDep
) -> SearchResponseAPISchema:
    search_task: SearchTask | None = search_service.get_search_task(search_id=search_id)
    if search_task is None:
        raise HTTPException(status_code=404, detail="search not found")
    return SearchResponseAPISchema(
        search_id=search_task.id,
        parsed_pages=search_task.parsed_pages,
        parsed_vacancies=search_task.parsed_count,
        status=search_task.state_machine.current_state_value,
    )


@vacancies_router.delete("/search/{search_id}")
async def delete_search(search_id: str, search_service: SearchServiceDep) -> None:
    search_task: SearchTask | None = search_service.get_search_task(search_id=search_id)
    if search_task is None:
        raise HTTPException(status_code=404, detail="search not found")
    await search_service.cancel_search(search_id=search_id)


@vacancies_router.get("/searches")
async def get_searches(session: SessionDep) -> Sequence[SearchHistoryModel]:
    result: Sequence[SearchHistoryORM] = await list_search_history(session=session)
    return list(map(lambda orm: search_history_to_model(orm=orm), result))


@vacancies_router.get(
    "/{vacancy_id}", status_code=status.HTTP_200_OK, summary="Find vacancy by ID"
)
async def find_by_id(vacancy_id: int, session: SessionDep) -> VacancyModel:
    result: VacancyORM | None = await get_vacancy(
        session=session, vacancy_id=vacancy_id
    )
    if result is not None:
        return vacancy_to_model(row=result)
    raise HTTPException(status_code=404, detail="Vacancy not found")


@vacancies_router.post(
    "/{vacancy_id}/submit", status_code=status.HTTP_200_OK, summary="Submit vacancy"
)
async def submit(
    vacancy_id: int, session: SessionDep, orchestrator: OrchestratorDep
) -> ApplicationStatusResponseAPISchema:
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
    return ApplicationStatusResponseAPISchema(
        vacancy_id=vacancy_id, status=application.status
    )


@vacancies_router.get("/{vacancy_id}/status")
async def get_status(
    vacancy_id: int, session: SessionDep
) -> ApplicationStatusResponseAPISchema:
    application: ApplicationORM | None = await get_application_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return ApplicationStatusResponseAPISchema(
        vacancy_id=vacancy_id, status=application.status
    )


@vacancies_router.post("/{vacancy_id}/queue_for_letter")
async def queue_for_letter(
    vacancy_id: int, session: SessionDep
) -> ApplicationStatusResponseAPISchema:
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
    return ApplicationStatusResponseAPISchema(
        vacancy_id=vacancy_id, status=application.status
    )


@vacancies_router.post("/{vacancy_id}/cover_letter")
async def cover_letter(
    vacancy_id: int, session: SessionDep, letter: CoverLetterRequest
) -> ApplicationStatusResponseAPISchema:
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
            to_state=ApplicationEvent.LETTER_GENERATED,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409,
            detail=f"Unavailable state for to submit cover letter. Error: {e}",
        )
    if application is None:
        raise HTTPException(status_code=500, detail="Server error")
    await create_cover_letter(
        session=session, application_id=application.id, text=letter.text
    )
    return ApplicationStatusResponseAPISchema(
        vacancy_id=vacancy_id, status=application.status
    )


@vacancies_router.post("/{vacancy_id}/retry")
async def retry(
    vacancy_id: int, session: SessionDep
) -> ApplicationStatusResponseAPISchema:
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
    return ApplicationStatusResponseAPISchema(
        vacancy_id=vacancy_id, status=application.status
    )
