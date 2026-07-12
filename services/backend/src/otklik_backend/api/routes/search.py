from fastapi import APIRouter, HTTPException, Response, status

from otklik_backend.api.dependencies import SearchServiceDep, SessionDep
from otklik_backend.api.schemas import (
    ConfirmSearchAPISchema,
    SearchHistoryAPISchema,
    SearchSessionAPISchema,
    VacanciesSearchAPISchema,
    VacanciesStartSearchRequestAPISchema,
)
from otklik_backend.db.converters import search_history_to_schema
from otklik_backend.db.repositories.search_history import SearchHistoryRepository
from otklik_backend.orchestrator.search import SearchSessionTask

search_router = APIRouter(prefix="/search", tags=["search"])

filter_router = APIRouter(prefix="/filter", tags=["search-filter"])
parse_router = APIRouter(prefix="/parse", tags=["search-parse"])


@filter_router.post("/new")
async def new_filter_session(
    search_service: SearchServiceDep,
) -> SearchSessionAPISchema:
    session_id: str = await search_service.open_filter_session()
    return SearchSessionAPISchema(session_id=session_id)


@filter_router.post("/{session_id}/confirm")
async def confirm_filter_session(
    session_id: str, search_service: SearchServiceDep
) -> ConfirmSearchAPISchema:
    url: str = await search_service.confirm_filter_session(session_id=session_id)
    return ConfirmSearchAPISchema(url=url)


@filter_router.post("/{session_id}/cancel")
async def cancel_filter_session(
    session_id: str, search_service: SearchServiceDep
) -> None:
    await search_service.cancel_filter_session(session_id=session_id)


@parse_router.post("/start", status_code=status.HTTP_200_OK, summary="Start parse task")
async def start_parse(
    filter: VacanciesStartSearchRequestAPISchema, search_service: SearchServiceDep
) -> VacanciesSearchAPISchema:
    search_task: SearchSessionTask = await search_service.open_search_session(
        request=filter
    )
    return VacanciesSearchAPISchema(
        search_id=search_task.id,
        parsed_pages=search_task.parsed_pages,
        parsed_vacancies=search_task.parsed_count,
        status=search_task.state_machine.current_state_value,
    )


@parse_router.get(
    "/current",
    response_model=VacanciesSearchAPISchema,
    responses={204: {"description": "No active parse task"}},
)
async def current_parse(
    search_service: SearchServiceDep,
) -> VacanciesSearchAPISchema | Response:
    search_task: SearchSessionTask | None = search_service.get_current_search_task()
    if search_task is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return VacanciesSearchAPISchema(
        search_id=search_task.id,
        parsed_pages=search_task.parsed_pages,
        parsed_vacancies=search_task.parsed_count,
        status=search_task.state_machine.current_state_value,
    )


@parse_router.delete("/{search_id}")
async def cancel_parse(search_id: str, search_service: SearchServiceDep) -> None:
    search_task: SearchSessionTask | None = search_service.find_search_task(
        search_id=search_id
    )
    if search_task is None:
        raise HTTPException(status_code=404, detail="search not found")
    await search_service.cancel_search_session(search_id=search_id)


@search_router.get("/history", summary="List past search runs (newest first)")
async def list_search_history(session: SessionDep) -> list[SearchHistoryAPISchema]:
    rows = await SearchHistoryRepository.list_all(session=session)
    return [search_history_to_schema(orm=row) for row in rows]


search_router.include_router(filter_router)
search_router.include_router(parse_router)
