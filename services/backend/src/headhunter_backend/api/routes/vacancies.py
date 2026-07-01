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
from headhunter_backend.db.models import ApplicationORM, CoverLetterORM, VacancyORM
from headhunter_backend.log import get_logger
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.db.repositories.search_history import SearchHistoryRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository

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
        rows: Sequence[VacancyORM] = await VacancyRepository.list_all(session=session)
    elif search_id == "latest":
        latest: str | None = await SearchHistoryRepository.get_latest_id(
            session=session
        )
        if latest is None:
            return []
        rows = await VacancyRepository.list_all(session=session, search_id=latest)
    else:
        rows = await VacancyRepository.list_all(session=session, search_id=search_id)
    return [vacancy_to_schema(row=row) for row in rows]


@vacancies_router.get(
    "/{vacancy_id}", status_code=status.HTTP_200_OK, summary="Find vacancy by ID"
)
async def find_by_id(vacancy_id: int, session: SessionDep) -> VacancyAPISchema:
    result: VacancyORM | None = await VacancyRepository.get_by_id(
        session=session, vacancy_id=vacancy_id
    )
    if result is not None:
        return vacancy_to_schema(row=result)
    raise HTTPException(status_code=404, detail="Vacancy not found")


@vacancies_router.get("/{vacancy_id}/status")
async def get_status(vacancy_id: int, session: SessionDep) -> ApplicationAPISchema:
    application: ApplicationORM | None = await ApplicationRepository.get_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return application_to_schema(orm=application)


@vacancies_router.get("/{vacancy_id}/cover_letter")
async def get_cover_letter(
    vacancy_id: int, session: SessionDep
) -> CoverLetterAPISchema:
    application: ApplicationORM | None = await ApplicationRepository.get_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    cover_letter: (
        CoverLetterORM | None
    ) = await CoverLetterRepository.get_latest_by_application_id(
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
    application: ApplicationORM | None = await ApplicationRepository.get_by_vacancy_id(
        vacancy_id=vacancy_id, session=session
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    cover_letters: Sequence[
        CoverLetterORM
    ] = await CoverLetterRepository.list_by_application_id(
        session=session, application_id=application.id
    )
    return [cover_letter_to_schema(orm=item) for item in cover_letters]
