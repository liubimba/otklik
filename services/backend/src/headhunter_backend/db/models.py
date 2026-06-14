from sqlalchemy import (
    JSON,
    Column,
    CheckConstraint,
    DateTime,
    Dialect,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator
from datetime import datetime
from typing import Any

from headhunter_backend.db.base import Base
from headhunter_backend.api.schemas import ProcessingState, SearchStatusAPISchema
from headhunter_backend.ai.deployment import LLMDeployment


search_vacancies_table = Table(
    "search_vacancies",
    Base.metadata,
    Column("search_id", String, ForeignKey("searches.id"), primary_key=True),
    Column("vacancy_id", Integer, ForeignKey("vacancies.id"), primary_key=True),
)


class LLMDeploymentList(TypeDecorator[list[LLMDeployment]]):
    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: list[LLMDeployment] | None, dialect: Dialect
    ) -> list[dict[str, Any]] | None:
        if value is None:
            return None
        return [deployment.model_dump(mode="json") for deployment in value]

    def process_result_value(
        self, value: list[dict[str, Any]] | None, dialect: Dialect
    ) -> list[LLMDeployment] | None:
        if value is None:
            return None
        return [LLMDeployment(**deployment) for deployment in value]


class SearchHistoryORM(Base):
    __tablename__ = "searches"
    id: Mapped[str] = mapped_column(primary_key=True)
    url: Mapped[str]
    max_vacancies: Mapped[int]
    max_pages: Mapped[int]
    status: Mapped[SearchStatusAPISchema] = mapped_column(Enum(SearchStatusAPISchema))
    parsed_vacancies: Mapped[int] = mapped_column(default=0)
    parsed_pages: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(default=None)


class RateLimitEventORM(Base):
    __tablename__ = "rate_limits"

    id: Mapped[int] = mapped_column(primary_key=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SettingsORM(Base):
    __tablename__ = "settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_settings_singleton"),)

    id: Mapped[int] = mapped_column(autoincrement=False, primary_key=True, default=1)

    letter_style: Mapped[str]
    resume_text: Mapped[str]

    max_pages: Mapped[int]
    max_vacancies: Mapped[int]

    daily_limit: Mapped[int]
    hourly_limit: Mapped[int]
    min_delay_ms: Mapped[int]
    delay_jitter_ms: Mapped[int]

    auto_submit: Mapped[bool] = mapped_column(default=False)

    llm_deployments: Mapped[list[LLMDeployment]] = mapped_column(
        LLMDeploymentList, default=list
    )
    llm_system_prompt: Mapped[str | None] = mapped_column(default=None)


class VacancyORM(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str]
    apply_link: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str]

    response_link: Mapped[str | None]
    company_stars: Mapped[str | None]
    salary: Mapped[str | None]
    company_name: Mapped[str | None]
    work_location: Mapped[str | None]
    updated_at: Mapped[str | None]
    published_at: Mapped[str | None]
    work_experience: Mapped[str | None]

    work_formats: Mapped[list[str]] = mapped_column(JSON)
    employment_types: Mapped[list[str]] = mapped_column(JSON)


class ApplicationORM(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)

    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id"), index=True, unique=True
    )
    status: Mapped[ProcessingState] = mapped_column(Enum(ProcessingState), index=True)
    retry_count: Mapped[int] = mapped_column(default=0, server_default="0")
    error_message: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=None, onupdate=datetime.now
    )


class CoverLetterORM(Base):
    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(primary_key=True)

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"), index=True
    )
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
