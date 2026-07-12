from typing import Literal

from pydantic import BaseModel

from otklik_backend.api.schemas import (
    AuthStatusAPISchema,
    VacancyAPISchema,
)
from otklik_backend.core.state import ProcessingState


class ApplicationData(BaseModel):
    vacancy_id: int
    application_id: int
    status: ProcessingState
    reason: str | None = None


class ApplicationWSEvent(BaseModel):
    type: Literal["application_event"] = "application_event"
    data: ApplicationData


class SearchData(BaseModel):
    search_id: str
    parsed_vacancies: int
    parsed_pages: int
    status: str


class SearchWSEvent(BaseModel):
    type: Literal["search_event"] = "search_event"
    data: SearchData


class CaptchaData(BaseModel):
    vacancy_id: int
    application_id: int


class CaptchaWSEvent(BaseModel):
    type: Literal["captcha_event"] = "captcha_event"
    data: CaptchaData


class VacancyWSEvent(BaseModel):
    type: Literal["vacancy_new"] = "vacancy_new"
    data: VacancyAPISchema
    search_id: str | None = None


class AuthWSEvent(BaseModel):
    type: Literal["auth_changed"] = "auth_changed"
    data: AuthStatusAPISchema
