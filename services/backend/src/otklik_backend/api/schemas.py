from datetime import datetime
from enum import Enum
from typing import Optional, Literal, Self, Sequence

from pydantic import BaseModel, Field, HttpUrl, field_validator

from otklik_backend.ai.deployment import LLMDeployment

from otklik_backend.core.state import ErrorDomain as ErrorDomain
from otklik_backend.core.state import ProcessingState as ProcessingState
from otklik_backend.secrets.store import SecretStorageMode
from otklik_backend.setup.claude_code import ClaudeCodeState
from otklik_backend.setup.hardware import HardwareSpecs
from otklik_backend.setup.ollama import OllamaState


class WorkFormat(str, Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"
    TRAVELING = "traveling"
    UNKNOWN = "unknown"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    ROTATIONAL = "rotational"
    PART_TIME = "part_time"
    SIDE_JOB = "side_job"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    UNKNOWN = "unknown"


class SearchStatusAPISchema(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELED = "canceled"
    FINISHED = "exited"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

    def is_active(self) -> bool:
        return self in (SearchStatusAPISchema.PENDING, SearchStatusAPISchema.RUNNING)


class VacancyAPISchema(BaseModel):
    id: Optional[int] = None

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


class VacancyStatusFilterAPISchema(str, Enum):
    NONE = "none"
    LETTER_PENDING = "letter_pending"
    LETTER_READY = "letter_ready"
    LETTER_REVIEWING = "letter_reviewing"
    LETTER_SENDING = "letter_sending"
    LETTER_SENT = "letter_sent"
    ERROR = "error"
    SKIPPED = "skipped"


class VacancyWithStatusAPISchema(VacancyAPISchema):
    status: Optional[ProcessingState] = None


class VacancyListPageAPISchema(BaseModel):
    items: list[VacancyWithStatusAPISchema]
    total: int


class SearchHistoryAPISchema(BaseModel):
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


class AICoverLetterAPISchema(BaseModel):
    text: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    was_fallback: bool
    cost_usd: Optional[float] = None


class AIHealthStatusAPISchema(BaseModel):
    status: str


class VacanciesStartSearchRequestAPISchema(BaseModel):
    url: HttpUrl
    max_pages: int | None = None
    max_vacancies: int | None = None

    @field_validator("url")
    @classmethod
    def _only_hh_ru(cls, v: HttpUrl) -> HttpUrl:
        if v.host is None or not v.host.endswith("hh.ru"):
            raise ValueError("URL must be on hh.ru")
        return v


class VacanciesSearchAPISchema(BaseModel):
    search_id: str
    status: SearchStatusAPISchema
    parsed_pages: int
    parsed_vacancies: int


class ApplicationAPISchema(BaseModel):
    vacancy_id: int
    retry_count: int
    application_id: int
    status: ProcessingState
    created_at: datetime
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None


class CoverLetterRequestAPISchema(BaseModel):
    text: str


class CoverLetterAPISchema(BaseModel):
    text: str
    version: int
    created_at: datetime


class ApplicationDetailAPISchema(BaseModel):
    vacancy_id: int
    application_id: int
    retry_count: int
    status: ProcessingState
    reason: Optional[str] = None
    error_domain: Optional[ErrorDomain] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    latest_letter: Optional[CoverLetterAPISchema] = None
    letters_count: int


class SubmitApplicationRequestAPISchema(BaseModel):
    text: Optional[str] = None


class ApplicationsSummaryAPISchema(BaseModel):
    needs_attention: int


class ChatMessageAPISchema(BaseModel):
    id: int
    role: str
    content: str
    produced_version: Optional[int] = None
    created_at: datetime


class LetterChatRequestAPISchema(BaseModel):
    message: str


class RateLimitsAPISchema(BaseModel):
    daily_limit: int = 30
    hourly_limit: int = 5
    min_delay_ms: int = 800
    delay_jitter_ms: int = 400


class LLMSettingsAPISchema(BaseModel):
    resume_text: str = ""
    letter_style: str = ""
    system_prompt: Optional[str] = None
    proxy_url: Optional[str] = None
    deployments: list[LLMDeployment] = Field(default_factory=list)


class LLMDeploymentWriteAPISchema(BaseModel):
    id: Optional[str] = None
    model: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None


class LLMSettingsWriteAPISchema(BaseModel):
    resume_text: str = ""
    letter_style: str = ""
    system_prompt: Optional[str] = None
    proxy_url: Optional[str] = None
    deployments: list[LLMDeploymentWriteAPISchema] = Field(default_factory=list)


class UserSettingsAPISchema(BaseModel):
    auto_submit: bool = False


class SearchSettingsAPISchema(BaseModel):
    max_pages: int = 5
    max_vacancies: int = 50


class SettingsAPISchema(BaseModel):
    search: SearchSettingsAPISchema = Field(default_factory=SearchSettingsAPISchema)
    user: UserSettingsAPISchema = Field(default_factory=UserSettingsAPISchema)
    llm: LLMSettingsAPISchema = Field(default_factory=LLMSettingsAPISchema)
    rate_limits: RateLimitsAPISchema = Field(default_factory=RateLimitsAPISchema)


class SettingsWriteAPISchema(BaseModel):
    search: SearchSettingsAPISchema = Field(default_factory=SearchSettingsAPISchema)
    user: UserSettingsAPISchema = Field(default_factory=UserSettingsAPISchema)
    llm: LLMSettingsWriteAPISchema = Field(default_factory=LLMSettingsWriteAPISchema)
    rate_limits: RateLimitsAPISchema = Field(default_factory=RateLimitsAPISchema)


class SecretStorageAPISchema(BaseModel):
    mode: SecretStorageMode


class AuthStatusAPISchema(BaseModel):
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


class OrchestratorStatusAPISchema(BaseModel):
    reason: Optional[str] = None
    paused: bool
    queue_size: int
    queue: Sequence[int] = Field(default_factory=list)


class RateLimitInfoAPISchema(BaseModel):
    used: int
    limit: int
    resets_at: datetime


class RateLimitsBudgetAPISchema(BaseModel):
    hourly: RateLimitInfoAPISchema
    daily: RateLimitInfoAPISchema


class SearchSessionAPISchema(BaseModel):
    session_id: str


class ConfirmSearchAPISchema(BaseModel):
    url: str


class SetupStateAPISchema(BaseModel):
    hardware: HardwareSpecs
    ollama: OllamaState
    has_deployment: bool
    local_model: str
    cloud_model: str
    claude_available: bool
    chromium_installed: bool


class LocalSetupStateAPISchema(BaseModel):
    ollama_state: OllamaState
    installed_models: list[str]
    recommended_tag: str
    recommended_installed: bool


class ClaudeModelOption(BaseModel):
    model: str
    label: str


class ClaudeSetupStateAPISchema(BaseModel):
    claude_state: ClaudeCodeState
    default_model: str
    model_options: list[ClaudeModelOption]


class TrialRequestAPISchema(BaseModel):
    deployment: LLMDeploymentWriteAPISchema
    deadline_sec: float
