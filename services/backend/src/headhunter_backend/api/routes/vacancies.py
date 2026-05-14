from fastapi import APIRouter, HTTPException, status
from headhunter_backend.api.schemas import (
    Vacancy,
    SearchFilter,
    SearchResponse,
    ResponseStatus,
    WriteRequest,
)
from headhunter_backend.api.mock import mock_vacancy

vacancies_router = APIRouter(prefix="/vacancies", tags=["vacancies"])


@vacancies_router.get(
    "/", status_code=status.HTTP_200_OK, summary="Find all searched vacancies"
)
def find_all() -> list[Vacancy]:
    return [mock_vacancy]


@vacancies_router.post(
    "/search", status_code=status.HTTP_200_OK, summary="Search vacancies by query"
)
def search(filter: SearchFilter) -> SearchResponse:
    return SearchResponse(search_id="search_123")


@vacancies_router.get(
    "/{vacancy_id}", status_code=status.HTTP_200_OK, summary="Find vacancy by ID"
)
def find_by_id(vacancy_id: int) -> Vacancy:
    if vacancy_id == mock_vacancy.vacancy_id:
        return mock_vacancy
    raise HTTPException(status_code=404, detail="Vacancy not found")


@vacancies_router.post(
    "/{vacancy_id}/write",
    status_code=status.HTTP_200_OK,
    summary="Write letter for vacancy into DataBase",
)
def write(vacancy_id: int, request: WriteRequest) -> ResponseStatus:
    if vacancy_id == mock_vacancy.vacancy_id:
        return ResponseStatus.ok()
    raise HTTPException(status_code=404, detail="Vacancy not found")


@vacancies_router.post(
    "/{vacancy_id}/submit", status_code=status.HTTP_200_OK, summary="Submit vacancy"
)
def submit(vacancy_id: int) -> ResponseStatus:
    if vacancy_id == mock_vacancy.vacancy_id:
        return ResponseStatus.ok()
    raise HTTPException(status_code=404, detail="Vacancy not found")
