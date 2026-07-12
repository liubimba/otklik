from typing import Annotated, Sequence

from fastapi import APIRouter, HTTPException, Query, status

from otklik_backend.api.dependencies import SessionDep
from otklik_backend.api.schemas import (
    VacancyAPISchema,
    VacancyListPageAPISchema,
    VacancyStatusFilterAPISchema,
)
from otklik_backend.core.state import ProcessingState
from otklik_backend.db.converters import (
    vacancy_to_schema,
    vacancy_with_status_to_schema,
)
from otklik_backend.db.models import VacancyORM
from otklik_backend.db.repositories.search_history import SearchHistoryRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.log import get_logger

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


# Must be declared before GET /{vacancy_id}: Starlette matches routes in
# declaration order, so "/all" would otherwise be captured by the int-typed
# {vacancy_id} path param and rejected with a 422 rather than falling through.
@vacancies_router.get(
    "/all",
    status_code=status.HTTP_200_OK,
    summary="List every vacancy with its application status (paginated)",
)
async def list_all_with_status(
    session: SessionDep,
    status_filter: Annotated[
        list[VacancyStatusFilterAPISchema] | None,
        Query(
            alias="status",
            description='Repeatable. "none" matches vacancies with no application yet.',
        ),
    ] = None,
    q: str | None = Query(
        default=None,
        max_length=200,
        description="Free-text search. Every word must appear in the title, "
        "company name or description.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> VacancyListPageAPISchema:
    chips = status_filter or []
    include_unapplied = VacancyStatusFilterAPISchema.NONE in chips
    statuses = [
        ProcessingState(chip.value)
        for chip in chips
        if chip is not VacancyStatusFilterAPISchema.NONE
    ]

    rows, total = await VacancyRepository.list_with_status(
        session=session,
        statuses=statuses,
        include_unapplied=include_unapplied,
        search=q,
        limit=limit,
        offset=offset,
    )
    return VacancyListPageAPISchema(
        items=[
            vacancy_with_status_to_schema(row=row, status=row_status)
            for row, row_status in rows
        ],
        total=total,
    )


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
