from typing import Self, Literal
from pydantic import BaseModel, Field
from headhunter_backend.domain.enums import ProcessingState


class SearchFilter(BaseModel):
    text: str


class SearchResponse(BaseModel):
    search_id: str


class ApplicationStatusResponse(BaseModel):
    vacancy_id: int
    status: ProcessingState


class CoverLetterRequest(BaseModel):
    text: str


## Settings
class RateLimits(BaseModel):
    daily_limit: int = 30
    hourly_limit: int = 5
    min_delay_ms: int = 800
    delay_jitter_ms: int = 400


class Settings(BaseModel):
    letter_style: str = ""
    resume_text: str = ""
    rate_limits: RateLimits = Field(default_factory=RateLimits)


## Auth
class AuthStatus(BaseModel):
    status: Literal["authorized", "unauthorized", "authorizing"]

    def is_authorized(self) -> bool:
        return self.status == "authorized"

    @classmethod
    def authorized(cls) -> Self:
        return cls(status="authorized")

    @classmethod
    def unauthorized(cls) -> Self:
        return cls(status="unauthorized")

    @classmethod
    def authorizing(cls) -> Self:
        return cls(status="authorizing")

    @classmethod
    def from_boolean(cls, authenticated: bool) -> Self:
        return cls.authorized() if authenticated else cls.unauthorized()
