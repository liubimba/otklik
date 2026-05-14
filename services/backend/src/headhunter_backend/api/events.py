from typing import Literal
from pydantic import BaseModel
from .schemas import Vacancy


class VacancyEvent(BaseModel):
    type: Literal["vacancy_new"] = "vacancy_new"
    data: Vacancy
    search_id: str | None = None
