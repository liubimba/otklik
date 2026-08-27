from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.schemas import ProcessingState, VacancyAPISchema
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.models import SettingsORM
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.orchestrator.retry import retry_errored_applications
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService


async def _set_auto_generate(
    session_factory: async_sessionmaker[AsyncSession], value: bool
) -> None:
    async with session_factory() as session:
        settings: SettingsORM = await SettingsRepository.get(session=session)
        settings.auto_generate = value
        await SettingsRepository.update(session=session, new_settings=settings)


async def _seed_errored(
    session_factory: async_sessionmaker[AsyncSession], vacancy: VacancyAPISchema
) -> int:
    async with session_factory() as session:
        vacancy_orm = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy)
        )
        application = await ApplicationRepository.create(
            session=session, vacancy_id=vacancy_orm.id
        )
        await ApplicationRepository.transition(
            session=session,
            application_id=application.id,
            to_state=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )
        await ApplicationRepository.transition(
            session=session,
            application_id=application.id,
            to_state=ApplicationEvent.FAIL,
        )
        return application.id


async def test_retries_errored_apps_when_auto_generate_is_on(
    session_factory: async_sessionmaker[AsyncSession],
    fake_state_service: StateTransitionService,
    vacancy_model: VacancyAPISchema,
) -> None:
    await _set_auto_generate(session_factory, True)
    app_id = await _seed_errored(session_factory, vacancy_model)

    async with session_factory() as session:
        retried = await retry_errored_applications(session, fake_state_service)
        await session.commit()

    assert retried == 1
    async with session_factory() as session:
        app = await ApplicationRepository.get_by_id(
            session=session, application_id=app_id
        )
        assert app is not None
        assert app.status == ProcessingState.LETTER_PENDING


async def test_does_nothing_when_auto_generate_is_off(
    session_factory: async_sessionmaker[AsyncSession],
    fake_state_service: StateTransitionService,
    vacancy_model: VacancyAPISchema,
) -> None:
    await _set_auto_generate(session_factory, False)
    app_id = await _seed_errored(session_factory, vacancy_model)

    async with session_factory() as session:
        retried = await retry_errored_applications(session, fake_state_service)
        await session.commit()

    assert retried == 0
    async with session_factory() as session:
        app = await ApplicationRepository.get_by_id(
            session=session, application_id=app_id
        )
        assert app is not None
        assert app.status == ProcessingState.ERROR
