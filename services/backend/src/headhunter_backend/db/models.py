from sqlalchemy import JSON, Enum, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from headhunter_backend.db.base import Base
from headhunter_backend.domain.enums import ProcessingState


class SettingsORM(Base):
    __tablename__ = "settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_settings_singleton"),)

    id: Mapped[int] = mapped_column(autoincrement=False, primary_key=True, default=1)

    letter_style: Mapped[str]
    resume_text: Mapped[str]

    daily_limit: Mapped[int]
    hourly_limit: Mapped[int]
    min_delay_ms: Mapped[int]
    delay_jitter_ms: Mapped[int]


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str]
    apply_link: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str]

    company_stars: Mapped[str | None]
    salary: Mapped[str | None]
    company_name: Mapped[str | None]
    work_location: Mapped[str | None]
    updated_at: Mapped[str | None]
    published_at: Mapped[str | None]
    work_experience: Mapped[str | None]

    work_formats: Mapped[list[str]] = mapped_column(JSON)
    employment_types: Mapped[list[str]] = mapped_column(JSON)


class Application(Base):
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


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(primary_key=True)

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"), index=True
    )
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
