"""Behaviour tests for AutoSubmitListener.

Companion to the /application/submit HTTP guard added on 2026-07-02: SUBMIT
must NOT fire while the LetterSendingWorker is paused, no matter which
entry point emits it. The auto-apply cascade
(PARSED → LETTER_PENDING → LETTER_READY → LETTER_SENDING) reaches
LETTER_SENDING via this listener instead of the HTTP endpoint, so the
same invariant needs its own regression suite here — the user reported
that after a 409 on manual Submit, hitting Regenerate produced a fresh
letter and the auto-submit listener silently moved the app into
LETTER_SENDING while the worker was still paused, reproducing the
"infinite letter-sending" state through the second code path.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.schemas import ProcessingState, VacancyAPISchema
from headhunter_backend.core.events import (
    ApplicationData,
    ApplicationWSEvent,
)
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.db.models import (
    ApplicationORM,
    SettingsORM,
)
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.settings import SettingsRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.orchestrator.listeners.auto_submit import AutoSubmitListener
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.orchestrator.state_service import StateTransitionService
from headhunter_backend.orchestrator.workers.letter_sending import LetterSendingWorker


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
    """Vacancy + application walked into LETTER_READY, mimicking the
    natural cascade Player pending → letter_generated. Returns
    (vacancy_id, application_id).
    """
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


async def test_repro_auto_submit_bypasses_paused_worker(
    session_factory: async_sessionmaker[AsyncSession],
    fake_orchestrator: LetterSendingWorker,
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    """Reproduces the second bug flow the user hit on 2026-07-02:

    1. Manual Submit was refused with 409 because the worker was paused
       on NOT_AUTHORIZED (previous fix in api/routes/application.py).
    2. User then hit Regenerate — LLM produced a fresh letter and the
       state machine landed in LETTER_READY.
    3. AutoSubmitListener saw the LETTER_READY ApplicationWSEvent, fired
       SUBMIT, transitioned to LETTER_SENDING. Worker was still paused.
       Application sat in LETTER_SENDING forever (spinner).

    After the fix, the listener must skip SUBMIT when the worker is
    paused — the application should stay in LETTER_READY and the user
    can re-authenticate before submitting.
    """
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
        # BUG (before fix): status == LETTER_SENDING → stuck.
        # FIX: listener skipped the transition → still LETTER_READY.
        assert application.status == ProcessingState.LETTER_READY


async def test_auto_submit_fires_when_worker_is_running(
    session_factory: async_sessionmaker[AsyncSession],
    fake_orchestrator: LetterSendingWorker,
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    """Positive counterpart: the happy path (worker running, auth OK) still
    ends in LETTER_SENDING. Guards against a fix that over-corrects and
    disables auto-submit entirely.
    """
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
