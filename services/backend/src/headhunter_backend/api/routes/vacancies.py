from fastapi import APIRouter, HTTPException, status
from headhunter_backend.api.schemas import (
    SearchFilter,
    SearchResponse,
    ApplicationStatusResponse,
    CoverLetterRequest,
)
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.db.models import Vacancy, Application
from headhunter_backend.db.converters import vacancy_to_model
from headhunter_backend.db.crud import (
    list_vacancies,
    get_vacancy,
    get_application_by_vacancy_id,
    create_cover_letter,
    transition_application,
    create_application,
)
from headhunter_backend.api.dependencies import SessionDep
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from statemachine.exceptions import TransitionNotAllowed
from typing import Sequence

vacancies_router = APIRouter(prefix="/vacancies", tags=["vacancies"])


@vacancies_router.get(
    "/", status_code=status.HTTP_200_OK, summary="Find all searched vacancies"
)
async def find_all(session: SessionDep) -> Sequence[VacancyModel]:
    result: Sequence[Vacancy] = await list_vacancies(session=session)
    return list(map(lambda orm: vacancy_to_model(row=orm), result))


@vacancies_router.post(
    "/search", status_code=status.HTTP_200_OK, summary="Search vacancies by query"
)
def search(filter: SearchFilter) -> SearchResponse:
    return SearchResponse(search_id="search_123")


@vacancies_router.get(
    "/{vacancy_id}", status_code=status.HTTP_200_OK, summary="Find vacancy by ID"
)
async def find_by_id(vacancy_id: int, session: SessionDep) -> VacancyModel:
    result: Vacancy | None = await get_vacancy(session=session, vacancy_id=vacancy_id)
    if result is not None:
        return vacancy_to_model(row=result)
    raise HTTPException(status_code=404, detail="Vacancy not found")


@vacancies_router.post(
    "/{vacancy_id}/submit", status_code=status.HTTP_200_OK, summary="Submit vacancy"
)
async def submit(vacancy_id: int, session: SessionDep) -> ApplicationStatusResponse:
    vacancy: Vacancy | None = await get_vacancy(session=session, vacancy_id=vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    application: Application | None = await get_application_by_vacancy_id(
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
    return ApplicationStatusResponse(vacancy_id=vacancy_id, status=application.status)


@vacancies_router.get("/{vacancy_id}/status")
async def get_status(vacancy_id: int, session: SessionDep) -> ApplicationStatusResponse:
    application: Application | None = await get_application_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return ApplicationStatusResponse(vacancy_id=vacancy_id, status=application.status)


@vacancies_router.post("/{vacancy_id}/queue_for_letter")
async def queue_for_letter(
    vacancy_id: int, session: SessionDep
) -> ApplicationStatusResponse:
    if await get_vacancy(session=session, vacancy_id=vacancy_id) is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    application: Application | None = await get_application_by_vacancy_id(
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
    return ApplicationStatusResponse(vacancy_id=vacancy_id, status=application.status)


@vacancies_router.post("/{vacancy_id}/cover_letter")
async def cover_letter(
    vacancy_id: int, session: SessionDep, letter: CoverLetterRequest
) -> ApplicationStatusResponse:
    vacancy: Vacancy | None = await get_vacancy(session=session, vacancy_id=vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    application: Application | None = await get_application_by_vacancy_id(
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
    return ApplicationStatusResponse(vacancy_id=vacancy_id, status=application.status)
