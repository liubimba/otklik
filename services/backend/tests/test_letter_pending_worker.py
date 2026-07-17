import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.schemas import (
    ProcessingState,
    VacancyAPISchema,
)
from otklik_backend.core.events import (
    ApplicationData,
    ApplicationWSEvent,
)
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.models import ApplicationORM
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.orchestrator.cover_letter_service import CoverLetterService
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService
from otklik_backend.orchestrator.workers.letter_pending import LetterPendingWorker


async def wait_until(predicate, timeout: float = 2.0, interval: float = 0.02) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        result = predicate()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return
        await asyncio.sleep(interval)
    raise AssertionError("Timed out waiting for predicate")


async def _seed_letter_pending(
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
        return vacancy_orm.id, application.id


async def test_worker_picks_up_pending_event_and_completes_generation(
    session_factory: async_sessionmaker[AsyncSession],
    fake_state_service: StateTransitionService,
    recording_broadcaster: EventBroadcaster,
    ai_layer_with_router,
    vacancy_model: VacancyAPISchema,
) -> None:
    from tests.test_ai import _fake_model_response

    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="Async-produced letter"
    )

    _, application_id = await _seed_letter_pending(session_factory, vacancy_model)

    service = CoverLetterService(
        session_maker=session_factory,
        ai_layer=ai_layer_with_router,
        state_service=fake_state_service,
    )
    worker = LetterPendingWorker(
        cover_letter_service=service,
        state_service=fake_state_service,
        session_maker=session_factory,
        broadcaster=recording_broadcaster,
    )
    worker.start()
    run_task = asyncio.create_task(worker.run())

    try:
        await recording_broadcaster.publish(
            event=ApplicationWSEvent(
                data=ApplicationData(
                    vacancy_id=1,
                    application_id=application_id,
                    status=ProcessingState.LETTER_PENDING,
                    reason=None,
                )
            )
        )

        async def is_ready() -> bool:
            async with session_factory() as session:
                app = await ApplicationRepository.get_by_id(
                    session=session, application_id=application_id
                )
                return app is not None and app.status == ProcessingState.LETTER_READY

        await wait_until(is_ready)

        assert ai_layer_with_router._router.acompletion.await_count >= 1
    finally:
        run_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await run_task
        worker.stop()
