import asyncio

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.schemas import ErrorDomain, VacancyAPISchema
from otklik_backend.api.subscribers import CallbackEventSubscriber
from otklik_backend.core.events import ApplicationWSEvent
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService


async def _drain(broadcaster: EventBroadcaster) -> None:
    while broadcaster._pending:
        pending = list(broadcaster._pending)
        await asyncio.gather(*pending, return_exceptions=True)


async def _seed_application(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> int:
    async with session_factory() as session:
        vacancy = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy_model)
        )
        app = await ApplicationRepository.create(session=session, vacancy_id=vacancy.id)
        return app.id


async def test_broadcast_carries_model_error_domain_on_fail(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    app_id = await _seed_application(session_factory, vacancy_model)
    broadcaster = EventBroadcaster()
    state_service = StateTransitionService(broadcaster=broadcaster)
    received: list[BaseModel] = []

    async def _collect(event: BaseModel) -> None:
        received.append(event)

    broadcaster.register(CallbackEventSubscriber.from_callback(_collect))

    async with session_factory() as session:
        await state_service.transition(
            session=session,
            application_id=app_id,
            event=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )
        await state_service.transition(
            session=session,
            application_id=app_id,
            event=ApplicationEvent.FAIL,
            error_message="connection refused",
        )
    await _drain(broadcaster)

    fail_event = received[-1]
    assert isinstance(fail_event, ApplicationWSEvent)
    assert fail_event.data.reason == "connection refused"
    assert fail_event.data.error_domain == ErrorDomain.MODEL


async def test_broadcast_carries_submission_error_domain_on_submission_failed(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    app_id = await _seed_application(session_factory, vacancy_model)
    broadcaster = EventBroadcaster()
    state_service = StateTransitionService(broadcaster=broadcaster)
    received: list[BaseModel] = []

    async def _collect(event: BaseModel) -> None:
        received.append(event)

    broadcaster.register(CallbackEventSubscriber.from_callback(_collect))

    async with session_factory() as session:
        await state_service.transition(
            session=session,
            application_id=app_id,
            event=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )
        await state_service.transition(
            session=session,
            application_id=app_id,
            event=ApplicationEvent.LETTER_GENERATED,
        )
        await state_service.transition(
            session=session,
            application_id=app_id,
            event=ApplicationEvent.SUBMIT,
        )
        await state_service.transition(
            session=session,
            application_id=app_id,
            event=ApplicationEvent.SUBMISSION_FAILED,
            reason="verification timeout",
        )
    await _drain(broadcaster)

    failed_event = received[-1]
    assert isinstance(failed_event, ApplicationWSEvent)
    assert failed_event.data.reason == "verification timeout"
    assert failed_event.data.error_domain == ErrorDomain.SUBMISSION
