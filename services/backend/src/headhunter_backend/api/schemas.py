from typing import Optional, Self
from datetime import datetime
from pydantic import BaseModel


## Vacancies
class Vacancy(BaseModel):
    vacancy_id: int
    name: str
    description: str
    salary: Optional[int]
    company_id: int
    company_name: str
    city: str
    created_at: datetime
    updated_at: datetime
    link: str


class SearchFilter(BaseModel):
    text: str


class SearchResponse(BaseModel):
    search_id: str


class WriteRequest(BaseModel):
    text: str


class ResponseStatus(BaseModel):
    success: bool

    @classmethod
    def ok(cls) -> Self:
        return cls(success=True)


## Settings
class RateLimits(BaseModel):
    daily_limit: int = 30
    hourly_limit: int = 5
    min_delay_ms: int = 800
    delay_jitter_ms: int = 400


class Settings(BaseModel):
    letter_style: str
    resume_text: str
    rate_limits: RateLimits
