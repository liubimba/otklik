"""Behavioural tests for LetterPendingWorker.

Since the /application/generate endpoint became async on 2026-07-02, the
LLM run for a fresh LETTER_PENDING is owned solely by this worker. The
endpoint only fires the state-machine transition; if the worker doesn't
actually pick up the resulting ApplicationWSEvent and drive it through
`cover_letter_service.regenerate`, the application would sit forever in
LETTER_PENDING and the UI spinner would never resolve.
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.schemas import (
    ProcessingState,
    VacancyAPISchema,
)
from headhunter_backend.core.events import (
    ApplicationData,
    ApplicationWSEvent,
)
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.db.models import ApplicationORM
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.orchestrator.cover_letter_service import CoverLetterService
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.orchestrator.state_service import StateTransitionService
from headhunter_backend.orchestrator.workers.letter_pending import LetterPendingWorker


async def wait_until(predicate, timeout: float = 2.0, interval: float = 0.02) -> None:
    """Poll `predicate` (sync or async) until it returns truthy or times out."""
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
    """End-to-end: publishing an ApplicationWSEvent(status=letter_pending)
    causes the worker to run the LLM (via CoverLetterService.regenerate)
    and drive the application to LETTER_READY, producing a cover letter
    version.

    This is the async half of the /generate rewrite: /generate only
    transitions to LETTER_PENDING and publishes the event; the LLM path
    lives here. If this test fails, the sheet would sit on the spinner
    forever after the user clicks Regenerate.
    """
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

        # LLM was invoked at least once. Exact call count depends on how
        # many health-check pings ai_layer fires around the generate
        # call — verifying LETTER_READY landed is a strong-enough signal
        # that the LLM ran (transition needs the completion result).
        assert ai_layer_with_router._router.acompletion.await_count >= 1
    finally:
        run_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await run_task
        worker.stop()
