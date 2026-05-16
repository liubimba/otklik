from typing import Literal
from pydantic import BaseModel
from .schemas import Vacancy, AuthStatus


class VacancyEvent(BaseModel):
    type: Literal["vacancy_new"] = "vacancy_new"
    data: Vacancy
    search_id: str | None = None


class AuthEvent(BaseModel):
    type: Literal["auth_changed"] = "auth_changed"
    data: AuthStatus
