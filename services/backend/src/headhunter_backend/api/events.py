from typing import Literal
from pydantic import BaseModel
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.api.schemas import AuthStatus


class CaptchaData(BaseModel):
    vacancy_id: int
    application_id: int


class CaptchaEvent(BaseModel):
    type: Literal["captcha_event"] = "captcha_event"
    data: CaptchaData


class VacancyEvent(BaseModel):
    type: Literal["vacancy_new"] = "vacancy_new"
    data: VacancyModel
    search_id: str | None = None


class AuthEvent(BaseModel):
    type: Literal["auth_changed"] = "auth_changed"
    data: AuthStatus


class SubmissionData(BaseModel):
    vacancy_id: int
    application_id: int
    succeeded: bool
    reason: str | None = None


class SubmissionEvent(BaseModel):
    type: Literal["submission_event"] = "submission_event"
    data: SubmissionData
