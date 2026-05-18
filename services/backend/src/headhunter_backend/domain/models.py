from pydantic import BaseModel
from typing import Optional
from .enums import WorkFormat, EmploymentType


class SalaryRange(BaseModel):
    salary_from: int
    salary_to: int


class VacancyModel(BaseModel):
    title: str
    apply_link: str
    description: str

    company_stars: Optional[str] = None
    salary: Optional[str] = None
    company_name: Optional[str] = None
    work_location: Optional[str] = None
    updated_at: Optional[str] = None
    published_at: Optional[str] = None
    work_formats: list[WorkFormat] = [WorkFormat.UNKNOWN]
    employment_types: list[EmploymentType] = [EmploymentType.UNKNOWN]
    work_experience: Optional[str] = None


class SearchModel(BaseModel):
    text: str
    region: Optional[str] = None
    salary: Optional[SalaryRange] = None
