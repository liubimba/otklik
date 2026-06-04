from typing import Self, Literal, Optional
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator
from headhunter_backend.domain.enums import ProcessingState
from headhunter_backend.ai.deployment import LLMDeployment


class AICoverLetterResponseAPISchema(BaseModel):
    text: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    was_fallback: bool
    cost_usd: Optional[float] = None


class AIHealthStatusAPISchema(BaseModel):
    status: str


class SearchStatusAPISchema(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELED = "canceled"
    FINISHED = "exited"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

    def is_active(self) -> bool:
        return self in (SearchStatusAPISchema.PENDING, SearchStatusAPISchema.RUNNING)


class SearchRequestAPISchema(BaseModel):
    url: HttpUrl
    max_pages: int = 5
    max_vacancies: int = 50

    @field_validator("url")
    @classmethod
    def _only_hh_ru(cls, v: HttpUrl) -> HttpUrl:
        if v.host is None or not v.host.endswith("hh.ru"):
            raise ValueError("URL must be on hh.ru")
        return v


class SearchResponseAPISchema(BaseModel):
    search_id: str
    status: SearchStatusAPISchema
    parsed_pages: int
    parsed_vacancies: int


class ApplicationStatusResponseAPISchema(BaseModel):
    vacancy_id: int
    status: ProcessingState


class CoverLetterRequest(BaseModel):
    text: str


## Settings
class RateLimitsAPISchema(BaseModel):
    daily_limit: int = 30
    hourly_limit: int = 5
    min_delay_ms: int = 800
    delay_jitter_ms: int = 400


class LLMSettingsAPISchema(BaseModel):
    resume_text: str = ""
    letter_style: str = ""
    system_prompt: Optional[str] = None
    deployments: list[LLMDeployment] = Field(default_factory=list)


class SettingsAPISchema(BaseModel):
    llm: LLMSettingsAPISchema = Field(default_factory=LLMSettingsAPISchema)
    rate_limits: RateLimitsAPISchema = Field(default_factory=RateLimitsAPISchema)


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
