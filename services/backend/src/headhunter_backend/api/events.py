from typing import Literal
from pydantic import BaseModel
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.api.schemas import AuthStatus


class VacancyEvent(BaseModel):
    type: Literal["vacancy_new"] = "vacancy_new"
    data: VacancyModel
    search_id: str | None = None


class AuthEvent(BaseModel):
    type: Literal["auth_changed"] = "auth_changed"
    data: AuthStatus
