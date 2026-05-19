from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from headhunter_backend.db.base import Base


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
