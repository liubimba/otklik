from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
)
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.db.models import Vacancy, Application, CoverLetter
from headhunter_backend.db.converters import vacancy_to_model, vacancy_to_orm
from headhunter_backend.db.crud import (
    create_vacancy,
    get_vacancy,
    get_vacancy_by_apply_link,
    list_vacancies,
    delete_vacancy,
    create_cover_letter,
    get_latest_cover_letter,
    create_application,
)


async def test_vacancy_crud(
    session_factory: async_sessionmaker[AsyncSession], vacancy_model: VacancyModel
) -> None:
    async with session_factory() as session:
        created: Vacancy = await create_vacancy(
            session=session, vacancy=vacancy_to_orm(model=vacancy_model)
        )
        vacancy_id: int = created.id
        assert vacancy_id is not None

    async with session_factory() as session:
        by_id: Vacancy = await get_vacancy(session=session, vacancy_id=vacancy_id)
        assert by_id is not None

        by_link: Vacancy = await get_vacancy_by_apply_link(
            session=session, apply_link=vacancy_model.apply_link
        )
        assert by_link is not None

        assert len(await list_vacancies(session=session)) == 1

        assert by_id.work_formats == ["remote", "hybrid"]
        assert by_id.employment_types == ["full_time", "part_time"]

        assert vacancy_to_model(row=by_id) == vacancy_model

    async with session_factory() as session:
        assert await delete_vacancy(session=session, vacancy_id=vacancy_id) is True
        assert await get_vacancy(session=session, vacancy_id=vacancy_id) is None
        assert await delete_vacancy(session=session, vacancy_id=vacancy_id) is False


async def test_cover_letter_crud(
    session_factory: async_sessionmaker[AsyncSession], vacancy_model: VacancyModel
) -> None:
    async with session_factory() as session:
        created_vacancy: Vacancy = await create_vacancy(
            session=session, vacancy=vacancy_to_orm(model=vacancy_model)
        )
        vacancy_id: int = created_vacancy.id

        created_application: Application = await create_application(
            session=session, vacancy_id=vacancy_id
        )
        application_id: int = created_application.id

        text: str = "Test"
        first_created: CoverLetter = await create_cover_letter(
            session=session, application_id=application_id, text=text
        )
        first_created_id: int = first_created.id

        assert first_created_id is not None
        assert first_created.text == text
        assert first_created.application_id == application_id
        assert first_created.version == 1

        text = text * 2
        second_created: CoverLetter = await create_cover_letter(
            session=session, application_id=application_id, text=text
        )

        assert second_created.id is not None
        assert second_created.id != first_created_id
        assert second_created.application_id == application_id
        assert second_created.version == 2
        assert second_created.text == text

        latest: CoverLetter = await get_latest_cover_letter(
            session=session, application_id=application_id
        )

        assert latest == second_created

        assert (
            await get_latest_cover_letter(session=session, application_id=999) is None
        )
