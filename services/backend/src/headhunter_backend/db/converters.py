from headhunter_backend.db.models import Vacancy
from headhunter_backend.domain.enums import EmploymentType, WorkFormat
from headhunter_backend.domain.models import VacancyModel


def vacancy_to_orm(model: VacancyModel) -> Vacancy:
    """Доменная модель → ORM-строка (без id — его назначит БД)."""
    return Vacancy(
        title=model.title,
        apply_link=model.apply_link,
        description=model.description,
        company_stars=model.company_stars,
        salary=model.salary,
        company_name=model.company_name,
        work_location=model.work_location,
        updated_at=model.updated_at,
        published_at=model.published_at,
        work_experience=model.work_experience,
        work_formats=[wf.value for wf in model.work_formats],
        employment_types=[et.value for et in model.employment_types],
    )


def vacancy_to_model(row: Vacancy) -> VacancyModel:
    """ORM-строка → доменная модель (id отбрасывается — его нет в VacancyModel)."""
    return VacancyModel(
        title=row.title,
        apply_link=row.apply_link,
        description=row.description,
        company_stars=row.company_stars,
        salary=row.salary,
        company_name=row.company_name,
        work_location=row.work_location,
        updated_at=row.updated_at,
        published_at=row.published_at,
        work_experience=row.work_experience,
        work_formats=[WorkFormat(v) for v in row.work_formats],
        employment_types=[EmploymentType(v) for v in row.employment_types],
    )
