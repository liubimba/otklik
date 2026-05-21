from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
)
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.db.models import Vacancy
from headhunter_backend.db.converters import vacancy_to_model, vacancy_to_orm
from headhunter_backend.domain.enums import WorkFormat, EmploymentType
from headhunter_backend.db.crud import (
    create_vacancy,
    get_vacancy,
    get_vacancy_by_apply_link,
    list_vacancies,
    delete_vacancy,
)


async def test_vacancy_crud(session_factory: async_sessionmaker[AsyncSession]) -> None:
    model: VacancyModel = VacancyModel(
        title="Python Developer",
        apply_link="https://hh.ru/vacancy/12345",
        description="Build and ship backend services.",
        company_name="ACME",
        salary="200000 RUB",
        work_formats=[WorkFormat.REMOTE, WorkFormat.HYBRID],
        employment_types=[EmploymentType.FULL_TIME, EmploymentType.PART_TIME],
        work_experience="1-3 years",
    )
    async with session_factory() as session:
        created: Vacancy = await create_vacancy(
            session=session, vacancy=vacancy_to_orm(model=model)
        )
        vacancy_id: str = created.id
        assert vacancy_id is not None

    async with session_factory() as session:
        by_id: Vacancy = await get_vacancy(session=session, vacancy_id=vacancy_id)
        assert by_id is not None

        by_link: Vacancy = await get_vacancy_by_apply_link(
            session=session, apply_link=model.apply_link
        )
        assert by_link is not None

        assert len(await list_vacancies(session=session)) == 1

        assert by_id.work_formats == ["remote", "hybrid"]
        assert by_id.employment_types == ["full_time", "part_time"]

        assert vacancy_to_model(row=by_id) == model

    async with session_factory() as session:
        assert await delete_vacancy(session=session, vacancy_id=vacancy_id) is True
        assert await get_vacancy(session=session, vacancy_id=vacancy_id) is None
        assert await delete_vacancy(session=session, vacancy_id=vacancy_id) is False
