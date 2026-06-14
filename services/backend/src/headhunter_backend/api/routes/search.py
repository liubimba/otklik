from fastapi import APIRouter, Response, status, HTTPException
from headhunter_backend.orchestrator.search import SearchTask
from headhunter_backend.api.dependencies import SearchServiceDep
from headhunter_backend.api.schemas import (
    SearchSessionAPISchema,
    ConfirmSearchAPISchema,
    VacanciesSearchAPISchema,
    VacanciesStartSearchRequestAPISchema,
)

search_router = APIRouter(prefix="/search", tags=["/search"])

picker = APIRouter(prefix="/picker", tags=["/picker"])
vacancies = APIRouter(prefix="/vacancies", tags=["/vacancies"])


@picker.post("/new")
async def new_session(search_service: SearchServiceDep) -> SearchSessionAPISchema:
    session_id: str = await search_service.start_filter_session()
    return SearchSessionAPISchema(session_id=session_id)


@picker.post("/{session_id}/confirm")
async def confirm_session(
    session_id: str, search_service: SearchServiceDep
) -> ConfirmSearchAPISchema:
    url: str = await search_service.confirm_session(session_id=session_id)
    return ConfirmSearchAPISchema(url=url)


@picker.post("/{session_id}/cancel")
async def cancel_session(session_id: str, search_service: SearchServiceDep) -> None:
    await search_service.cancel_session(session_id=session_id)


@vacancies.post(
    "/new", status_code=status.HTTP_200_OK, summary="Search vacancies by query"
)
async def new_search_vacancies(
    filter: VacanciesStartSearchRequestAPISchema, search_service: SearchServiceDep
) -> VacanciesSearchAPISchema:
    search_task: SearchTask = await search_service.start_search(request=filter)
    return VacanciesSearchAPISchema(
        search_id=search_task.id,
        parsed_pages=search_task.parsed_pages,
        parsed_vacancies=search_task.parsed_count,
        status=search_task.state_machine.current_state_value,
    )


@vacancies.get(
    "/current",
    response_model=VacanciesSearchAPISchema,
    responses={204: {"description": "No active search"}},
)
async def get_current_search_session(
    search_service: SearchServiceDep,
) -> VacanciesSearchAPISchema | Response:
    search_task: SearchTask | None = search_service.get_current_search_task()
    if search_task is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return VacanciesSearchAPISchema(
        search_id=search_task.id,
        parsed_pages=search_task.parsed_pages,
        parsed_vacancies=search_task.parsed_count,
        status=search_task.state_machine.current_state_value,
    )


@vacancies.get("/{search_id}")
async def find_search(
    search_id: str, search_service: SearchServiceDep
) -> VacanciesSearchAPISchema:
    search_task: SearchTask | None = search_service.get_search_task(search_id=search_id)
    if search_task is None:
        raise HTTPException(status_code=404, detail="search not found")
    return VacanciesSearchAPISchema(
        search_id=search_task.id,
        parsed_pages=search_task.parsed_pages,
        parsed_vacancies=search_task.parsed_count,
        status=search_task.state_machine.current_state_value,
    )


@vacancies.delete("/{search_id}")
async def delete_search(search_id: str, search_service: SearchServiceDep) -> None:
    search_task: SearchTask | None = search_service.get_search_task(search_id=search_id)
    if search_task is None:
        raise HTTPException(status_code=404, detail="search not found")
    await search_service.cancel_search(search_id=search_id)


search_router.include_router(picker)
search_router.include_router(vacancies)
