from pydantic import BaseModel
from typing import Optional
from .enums import WorkFormat, EmploymentType
from datetime import datetime
from headhunter_backend.api.schemas import SearchStatusAPISchema


class SalaryRange(BaseModel):
    salary_from: int
    salary_to: int


class VacancyModel(BaseModel):
    title: str
    apply_link: str
    description: str

    response_link: Optional[str] = None
    company_stars: Optional[str] = None
    salary: Optional[str] = None
    company_name: Optional[str] = None
    work_location: Optional[str] = None
    updated_at: Optional[str] = None
    published_at: Optional[str] = None
    work_formats: list[WorkFormat] = [WorkFormat.UNKNOWN]
    employment_types: list[EmploymentType] = [EmploymentType.UNKNOWN]
    work_experience: Optional[str] = None


class SearchHistoryModel(BaseModel):
    id: str
    url: str
    max_vacancies: int
    max_pages: int
    status: SearchStatusAPISchema
    parsed_vacancies: Optional[int]
    parsed_pages: Optional[int]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error: Optional[str]
