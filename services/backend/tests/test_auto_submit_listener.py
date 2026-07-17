import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.schemas import ProcessingState, VacancyAPISchema
from otklik_backend.core.events import (
    ApplicationData,
    ApplicationWSEvent,
)
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.models import (
    ApplicationORM,
    SettingsORM,
)
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.orchestrator.listeners.auto_submit import AutoSubmitListener
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService
from otklik_backend.orchestrator.workers.letter_sending import LetterSendingWorker


async def _drain(broadcaster: EventBroadcaster) -> None:
    while broadcaster._pending:
        pending = list(broadcaster._pending)
        await asyncio.gather(*pending, return_exceptions=True)


async def _enable_auto_submit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        settings: SettingsORM = await SettingsRepository.get(session=session)
        settings.auto_submit = True
        await SettingsRepository.update(session=session, new_settings=settings)


async def _seed_letter_ready(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy: VacancyAPISchema,
) -> tuple[int, int]:
    async with session_factory() as session:
        vacancy_orm = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy)
        )
        application: ApplicationORM = await ApplicationRepository.create(
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
            to_state=ApplicationEvent.LETTER_GENERATED,
        )
        return vacancy_orm.id, application.id


async def test_auto_submit_does_not_fire_when_worker_is_paused_for_auth(
    session_factory: async_sessionmaker[AsyncSession],
    fake_orchestrator: LetterSendingWorker,
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    await _enable_auto_submit(session_factory)
    _, application_id = await _seed_letter_ready(session_factory, vacancy_model)

    listener = AutoSubmitListener(
        state_service=fake_state_service,
        session_maker=session_factory,
        broadcaster=recording_broadcaster,
        letter_sending_worker=fake_orchestrator,
    )
    listener.start()

    fake_orchestrator.pause(reason=fake_orchestrator.PAUSE_REASON_NOT_AUTHORIZED)

    await recording_broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=1,
                application_id=application_id,
                status=ProcessingState.LETTER_READY,
                reason=None,
            )
        )
    )
    await _drain(recording_broadcaster)

    async with session_factory() as session:
        application = await ApplicationRepository.get_by_id(
            session=session, application_id=application_id
        )
        assert application is not None
        assert application.status == ProcessingState.LETTER_READY


async def test_auto_submit_fires_when_worker_is_running(
    session_factory: async_sessionmaker[AsyncSession],
    fake_orchestrator: LetterSendingWorker,
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    await _enable_auto_submit(session_factory)
    _, application_id = await _seed_letter_ready(session_factory, vacancy_model)

    listener = AutoSubmitListener(
        state_service=fake_state_service,
        session_maker=session_factory,
        broadcaster=recording_broadcaster,
        letter_sending_worker=fake_orchestrator,
    )
    listener.start()

    assert not fake_orchestrator.is_paused()

    await recording_broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=1,
                application_id=application_id,
                status=ProcessingState.LETTER_READY,
                reason=None,
            )
        )
    )
    await _drain(recording_broadcaster)

    async with session_factory() as session:
        application = await ApplicationRepository.get_by_id(
            session=session, application_id=application_id
        )
        assert application is not None
        assert application.status == ProcessingState.LETTER_SENDING
