from typing import Sequence

from fastapi import APIRouter, HTTPException, Query, status

from headhunter_backend.api.dependencies import SessionDep
from headhunter_backend.api.schemas import (
    ApplicationAPISchema,
    CoverLetterAPISchema,
    VacancyAPISchema,
)
from headhunter_backend.db.converters import (
    application_to_schema,
    cover_letter_to_schema,
    vacancy_to_schema,
)
from headhunter_backend.db.crud import (
    get_application_by_vacancy_id,
    get_latest_cover_letter,
    get_latest_search_id,
    get_vacancy,
    list_cover_letters_by_application_id,
    list_vacancies,
)
from headhunter_backend.db.models import ApplicationORM, CoverLetterORM, VacancyORM
from headhunter_backend.log import get_logger

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


@vacancies_router.get("/{vacancy_id}/status")
async def get_status(vacancy_id: int, session: SessionDep) -> ApplicationAPISchema:
    application: ApplicationORM | None = await get_application_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
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
    return [cover_letter_to_schema(orm=item) for item in cover_letters]
