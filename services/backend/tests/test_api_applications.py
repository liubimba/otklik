from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.api.schemas import ApplicationAPISchema, VacancyAPISchema
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository


async def test_api_empty_list_applications(client) -> None:
    response = client.get("/api/v1/applications")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 0


async def test_api_list_applications(
    client,
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    async with session_factory() as session:
        vacancy_model.apply_link = vacancy_model.apply_link + "/1"
        await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy_model)
        )
        vacancy_model.apply_link = vacancy_model.apply_link + "/2"
        await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy_model)
        )

        application1 = await ApplicationRepository.create(session=session, vacancy_id=1)
        application2 = await ApplicationRepository.create(session=session, vacancy_id=2)

    response = client.get("/api/v1/applications")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert payload[0]["application_id"] == application2.id
    assert payload[0]["vacancy_id"] == application2.vacancy_id
    assert payload[1]["application_id"] == application1.id
    assert payload[1]["vacancy_id"] == application1.vacancy_id


async def test_api_get_application_by_id(
    client,
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    async with session_factory() as session:
        vacancy_model.apply_link = vacancy_model.apply_link + "/1"
        await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy_model)
        )

        application = await ApplicationRepository.create(session=session, vacancy_id=1)

    response = client.get("/api/v1/applications/1")
    assert response.status_code == 200
    payload = response.json()
    schema: ApplicationAPISchema = ApplicationAPISchema.model_validate(payload)
    assert application.vacancy_id == schema.vacancy_id
