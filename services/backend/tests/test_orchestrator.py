from otklik_backend.orchestrator.workers.letter_sending import LetterSendingWorker
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.api.schemas import ProcessingState, VacancyAPISchema
from tests.conftest import (
    FakeWriter,
    FakeBrowser,
    RecordingBroadcaster,
    wait_until,
)

import asyncio

from unittest.mock import patch

from otklik_backend.core.site.result import SubmissionResult
from otklik_backend.db.models import RateLimitEventORM
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.orchestrator.auto_apply_canceller import AutoApplyCanceller
from otklik_backend.orchestrator.state_service import StateTransitionService
from otklik_backend.core.events import CaptchaWSEvent, ApplicationWSEvent
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.cover_letters import CoverLetterRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from sqlalchemy import select, func


async def test_recover_picks_up_queued_and_stale_sending(
    fake_orchestrator: LetterSendingWorker,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    picked: list[int] = []
    async with session_factory() as session:
        for index in range(5):
            await VacancyRepository.create(
                session=session,
                vacancy=vacancy_to_orm(
                    VacancyAPISchema(
                        title="t", apply_link=f"link{index}", description="d"
                    )
                ),
            )

        for vacancy_id, status in (
            (1, ProcessingState.LETTER_QUEUED),
            (2, ProcessingState.LETTER_QUEUED),
            (3, ProcessingState.LETTER_SENDING),
            (4, ProcessingState.LETTER_SENT),
            (5, ProcessingState.SKIPPED),
        ):
            app = await ApplicationRepository.create(
                session=session, vacancy_id=vacancy_id
            )
            app.status = status
            if status in (
                ProcessingState.LETTER_QUEUED,
                ProcessingState.LETTER_SENDING,
            ):
                picked.append(app.id)
        await session.commit()

        recovered = await fake_orchestrator.recover(session=session)
        assert recovered == len(picked)
        assert fake_orchestrator.qsize() == len(picked)
        drained = {await fake_orchestrator.get_next() for _ in range(len(picked))}
        assert drained == set(picked)
        assert fake_orchestrator.qsize() == 0


async def test_enqueue_then_get_next(fake_orchestrator: LetterSendingWorker) -> None:
    await fake_orchestrator.enqueue(application_id=42)
    assert fake_orchestrator.qsize() == 1
    next_id: int = await fake_orchestrator.get_next()
    assert next_id == 42
    assert fake_orchestrator.qsize() == 0


async def seed_app_in_letter_sending(
    session_factory: async_sessionmaker[AsyncSession],
    apply_link: str = "https://hh.ru/vacancy/1",
) -> int:
    async with session_factory() as session:
        await VacancyRepository.create(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(
                    title="t",
                    apply_link=apply_link,
                    description="d",
                )
            ),
        )
        app = await ApplicationRepository.create(session=session, vacancy_id=1)
        app.status = ProcessingState.LETTER_SENDING
        await CoverLetterRepository.create(
            session=session, application_id=app.id, text="hi"
        )
        await session.commit()
        return app.id


async def seed_app_in_letter_queued(
    session_factory: async_sessionmaker[AsyncSession],
    apply_link: str = "https://hh.ru/vacancy/1",
) -> int:
    async with session_factory() as session:
        await VacancyRepository.create(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(
                    title="t",
                    apply_link=apply_link,
                    description="d",
                )
            ),
        )
        app = await ApplicationRepository.create(session=session, vacancy_id=1)
        app.status = ProcessingState.LETTER_QUEUED
        await CoverLetterRepository.create(
            session=session, application_id=app.id, text="hi"
        )
        await session.commit()
        return app.id


async def test_process_one_flips_queued_to_sending_before_writer(
    fake_orchestrator: LetterSendingWorker,
    fake_writer: FakeWriter,
    authenticated_browser: FakeBrowser,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app_id = await seed_app_in_letter_queued(session_factory)
    fake_writer.queue(SubmissionResult.submitted())

    submitted = await fake_orchestrator._process_one(application_id=app_id)

    assert submitted is True
    assert len(fake_writer.calls) == 1

    statuses = [
        e.data.status
        for e in recording_broadcaster.events
        if isinstance(e, ApplicationWSEvent) and e.data.application_id == app_id
    ]
    assert ProcessingState.LETTER_SENDING in statuses
    assert statuses.index(ProcessingState.LETTER_SENDING) < statuses.index(
        ProcessingState.LETTER_SENT
    )

    async with session_factory() as s:
        app = await ApplicationRepository.get_by_id(session=s, application_id=app_id)
        assert app is not None
        assert app.status == ProcessingState.LETTER_SENT


async def test_process_one_skips_application_still_in_letter_ready(
    fake_orchestrator: LetterSendingWorker,
    fake_writer: FakeWriter,
    authenticated_browser: FakeBrowser,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app_id = await _seed_app(
        session_factory, "https://hh.ru/vacancy/77", ProcessingState.LETTER_READY
    )

    submitted = await fake_orchestrator._process_one(application_id=app_id)

    assert submitted is False
    assert fake_writer.calls == []


async def start_consumer(
    orchestrator: LetterSendingWorker,
    writer: FakeWriter,
    browser: FakeBrowser,
    broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> asyncio.Task:
    return asyncio.create_task(orchestrator.run())


async def stop_consumer(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_writer_receives_vacancy_apply_link_as_url(
    fake_orchestrator: LetterSendingWorker,
    fake_writer: FakeWriter,
    authenticated_browser: FakeBrowser,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    apply_url = "https://hh.ru/vacancy/12345"
    app_id = await seed_app_in_letter_sending(session_factory, apply_link=apply_url)

    task = await start_consumer(
        fake_orchestrator,
        fake_writer,
        authenticated_browser,
        recording_broadcaster,
        session_factory,
    )
    try:
        await fake_orchestrator.enqueue(application_id=app_id)
        await wait_until(lambda: len(fake_writer.calls) == 1)
        assert fake_writer.calls[0]["uri"] == apply_url
    finally:
        await stop_consumer(task)


async def test_consume_submitted_transitions_and_logs(
    fake_orchestrator: LetterSendingWorker,
    fake_writer: FakeWriter,
    authenticated_browser: FakeBrowser,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)
    fake_writer.queue(SubmissionResult.submitted())

    task = await start_consumer(
        fake_orchestrator,
        fake_writer,
        authenticated_browser,
        recording_broadcaster,
        session_factory,
    )
    try:
        await fake_orchestrator.enqueue(application_id=app_id)

        async def status_is_sent() -> bool:
            async with session_factory() as s:
                app = await ApplicationRepository.get_by_id(
                    session=s, application_id=app_id
                )
                return app is not None and app.status == ProcessingState.LETTER_SENT

        await wait_until(status_is_sent)

        async with session_factory() as s:
            count = (
                await s.execute(select(func.count(RateLimitEventORM.id)))
            ).scalar_one()
            assert count == 1

        submissions = [
            e for e in recording_broadcaster.events if isinstance(e, ApplicationWSEvent)
        ]
        assert len(submissions) == 1
        assert submissions[0].data.status is ProcessingState.LETTER_SENT
        assert submissions[0].data.application_id == app_id
    finally:
        await stop_consumer(task)


async def _seed_app(
    session_factory: async_sessionmaker[AsyncSession],
    apply_link: str,
    status: ProcessingState,
) -> int:
    async with session_factory() as session:
        vacancy = await VacancyRepository.create(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(title="t", apply_link=apply_link, description="d")
            ),
        )
        app = await ApplicationRepository.create(session=session, vacancy_id=vacancy.id)
        app.status = status
        await session.commit()
        return app.id


async def test_cancel_pending_clears_workers_and_skips_queued_applications(
    fake_orchestrator: LetterSendingWorker,
    fake_state_service: "StateTransitionService",
    fake_browser: FakeBrowser,
    fake_writer: FakeWriter,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    pending_id = await _seed_app(
        session_factory, "https://hh.ru/vacancy/10", ProcessingState.LETTER_PENDING
    )
    sending_id = await _seed_app(
        session_factory, "https://hh.ru/vacancy/11", ProcessingState.LETTER_SENDING
    )

    pending_worker = LetterSendingWorker(
        state_service=fake_state_service,
        session_maker=session_factory,
        auth_flow=fake_browser,  # type: ignore[arg-type]
        writer=fake_writer,  # type: ignore[arg-type]
        broadcaster=recording_broadcaster,
    )
    await pending_worker.enqueue(application_id=pending_id)
    await fake_orchestrator.enqueue(application_id=sending_id)

    canceller = AutoApplyCanceller(
        letter_pending_worker=pending_worker,  # type: ignore[arg-type]
        letter_sending_worker=fake_orchestrator,
        state_service=fake_state_service,
        session_maker=session_factory,
    )

    count = await canceller.cancel_pending()

    assert count == 2
    assert pending_worker.qsize() == 0
    assert fake_orchestrator.qsize() == 0

    async with session_factory() as s:
        pending_app = await ApplicationRepository.get_by_id(
            session=s, application_id=pending_id
        )
        sending_app = await ApplicationRepository.get_by_id(
            session=s, application_id=sending_id
        )
    assert pending_app is not None and pending_app.status == ProcessingState.SKIPPED
    assert sending_app is not None and sending_app.status == ProcessingState.SKIPPED


async def test_pace_after_submission_waits_the_configured_min_delay(
    fake_orchestrator: LetterSendingWorker,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as s:
        settings = await SettingsRepository.get(session=s)
        settings.min_delay_ms = 5000
        settings.delay_jitter_ms = 0
        await s.commit()

    sleeps: list[float] = []
    real_sleep = asyncio.sleep

    async def record_sleep(delay: float) -> None:
        sleeps.append(delay)
        await real_sleep(0)

    with patch(
        "otklik_backend.orchestrator.workers.letter_sending.asyncio.sleep",
        side_effect=record_sleep,
    ):
        await fake_orchestrator._pace_after_submission()

    assert sleeps == [5.0]


async def test_process_one_reports_a_real_submission_so_the_loop_can_pace(
    fake_orchestrator: LetterSendingWorker,
    fake_writer: FakeWriter,
    authenticated_browser: FakeBrowser,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)
    fake_writer.queue(SubmissionResult.submitted())

    submitted = await fake_orchestrator._process_one(application_id=app_id)

    assert submitted is True


async def test_process_one_does_not_report_a_submission_on_failure(
    fake_orchestrator: LetterSendingWorker,
    fake_writer: FakeWriter,
    authenticated_browser: FakeBrowser,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)
    fake_writer.queue(SubmissionResult.failed(reason="boom"))

    submitted = await fake_orchestrator._process_one(application_id=app_id)

    assert submitted is False


async def test_consume_failed_transitions_to_error(
    fake_orchestrator,
    fake_writer,
    authenticated_browser,
    recording_broadcaster,
    session_factory,
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)
    fake_writer.queue(SubmissionResult.failed(reason="boom"))

    task = await start_consumer(
        fake_orchestrator,
        fake_writer,
        authenticated_browser,
        recording_broadcaster,
        session_factory,
    )
    try:
        await fake_orchestrator.enqueue(application_id=app_id)

        async def status_is_error() -> bool:
            async with session_factory() as s:
                app = await ApplicationRepository.get_by_id(
                    session=s, application_id=app_id
                )
                return app is not None and app.status == ProcessingState.ERROR

        await wait_until(status_is_error)

        submissions = [
            e for e in recording_broadcaster.events if isinstance(e, ApplicationWSEvent)
        ]
        assert len(submissions) == 1
        assert submissions[0].data.status is ProcessingState.ERROR
        assert submissions[0].data.reason == "boom"

        async with session_factory() as s:
            app = await ApplicationRepository.get_by_id(
                session=s, application_id=app_id
            )
            assert app is not None
            assert app.error_message == "boom"
    finally:
        await stop_consumer(task)


async def test_consume_captcha_pauses_and_reenqueues(
    fake_orchestrator,
    fake_writer,
    authenticated_browser,
    recording_broadcaster,
    session_factory,
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)
    fake_writer.queue(SubmissionResult.captcha())

    task = await start_consumer(
        fake_orchestrator,
        fake_writer,
        authenticated_browser,
        recording_broadcaster,
        session_factory,
    )
    try:
        await fake_orchestrator.enqueue(application_id=app_id)

        await asyncio.wait_for(fake_writer.invoked.wait(), timeout=2.0)
        await wait_until(
            lambda: fake_orchestrator.is_paused() and fake_orchestrator.qsize() == 1
        )

        async with session_factory() as s:
            app = await ApplicationRepository.get_by_id(
                session=s, application_id=app_id
            )
            assert app is not None
            assert app.status == ProcessingState.LETTER_SENDING

        captchas = [
            e for e in recording_broadcaster.events if isinstance(e, CaptchaWSEvent)
        ]
        assert len(captchas) == 1
        assert captchas[0].data.application_id == app_id
    finally:
        await stop_consumer(task)


async def test_worker_auto_resumes_on_authorized_ws_event(
    fake_orchestrator: LetterSendingWorker,
    recording_broadcaster: RecordingBroadcaster,
) -> None:
    from otklik_backend.api.schemas import AuthStatusAPISchema
    from otklik_backend.core.events import AuthWSEvent

    fake_orchestrator.start()
    try:
        fake_orchestrator.pause(reason=fake_orchestrator.PAUSE_REASON_NOT_AUTHORIZED)
        assert fake_orchestrator.is_paused()

        await recording_broadcaster.publish(
            event=AuthWSEvent(data=AuthStatusAPISchema.authorized())
        )

        await wait_until(lambda: not fake_orchestrator.is_paused())
        assert fake_orchestrator.get_pause_reason() is None
    finally:
        fake_orchestrator.stop()


async def test_worker_does_not_auto_resume_when_still_unauthorized(
    fake_orchestrator: LetterSendingWorker,
    recording_broadcaster: RecordingBroadcaster,
) -> None:
    from otklik_backend.api.schemas import AuthStatusAPISchema
    from otklik_backend.core.events import AuthWSEvent

    fake_orchestrator.start()
    try:
        fake_orchestrator.pause(reason=fake_orchestrator.PAUSE_REASON_NOT_AUTHORIZED)
        for status in (
            AuthStatusAPISchema.unauthorized(),
            AuthStatusAPISchema.authorizing(),
        ):
            await recording_broadcaster.publish(event=AuthWSEvent(data=status))
        await asyncio.sleep(0.05)
        assert fake_orchestrator.is_paused()
    finally:
        fake_orchestrator.stop()


async def test_worker_does_not_auto_resume_when_paused_for_other_reason(
    fake_orchestrator: LetterSendingWorker,
    recording_broadcaster: RecordingBroadcaster,
) -> None:
    from otklik_backend.api.schemas import AuthStatusAPISchema
    from otklik_backend.core.events import AuthWSEvent

    fake_orchestrator.start()
    try:
        fake_orchestrator.pause(reason="captcha")
        await recording_broadcaster.publish(
            event=AuthWSEvent(data=AuthStatusAPISchema.authorized())
        )
        await asyncio.sleep(0.05)
        assert fake_orchestrator.is_paused()
        assert fake_orchestrator.get_pause_reason() == "captcha"
    finally:
        fake_orchestrator.stop()


async def test_worker_auth_event_is_a_no_op_when_not_paused(
    fake_orchestrator: LetterSendingWorker,
    recording_broadcaster: RecordingBroadcaster,
) -> None:
    from otklik_backend.api.schemas import AuthStatusAPISchema
    from otklik_backend.core.events import AuthWSEvent

    fake_orchestrator.start()
    try:
        assert not fake_orchestrator.is_paused()
        await recording_broadcaster.publish(
            event=AuthWSEvent(data=AuthStatusAPISchema.authorized())
        )
        await asyncio.sleep(0.05)
        assert not fake_orchestrator.is_paused()
    finally:
        fake_orchestrator.stop()


async def test_consume_not_authorized_fails(
    fake_orchestrator,
    fake_writer,
    fake_browser,
    recording_broadcaster,
    session_factory,
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)

    task = await start_consumer(
        fake_orchestrator,
        fake_writer,
        fake_browser,
        recording_broadcaster,
        session_factory,
    )
    try:
        await fake_orchestrator.enqueue(application_id=app_id)

        async def status_is_error() -> bool:
            async with session_factory() as s:
                app = await ApplicationRepository.get_by_id(
                    session=s, application_id=app_id
                )
                return app is not None and app.status == ProcessingState.ERROR

        await wait_until(status_is_error)

        assert fake_writer.calls == []
        submissions = [
            e for e in recording_broadcaster.events if isinstance(e, ApplicationWSEvent)
        ]
        assert len(submissions) == 1
        assert submissions[0].data.reason == "not authorized"
    finally:
        await stop_consumer(task)


async def test_consume_rate_limit_reenqueues_without_calling_writer(
    fake_orchestrator,
    fake_writer,
    authenticated_browser,
    recording_broadcaster,
    session_factory,
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)

    async with session_factory() as s:
        for _ in range(5):
            s.add(RateLimitEventORM())
        await s.commit()

    task = await start_consumer(
        fake_orchestrator,
        fake_writer,
        authenticated_browser,
        recording_broadcaster,
        session_factory,
    )
    try:
        await fake_orchestrator.enqueue(application_id=app_id)

        await wait_until(lambda: fake_orchestrator.qsize() >= 1)

        assert fake_writer.calls == []
        async with session_factory() as s:
            app = await ApplicationRepository.get_by_id(
                session=s, application_id=app_id
            )
            assert app is not None
            assert app.status == ProcessingState.LETTER_SENDING
    finally:
        await stop_consumer(task)


async def test_consume_missing_cover_letter_fails(
    fake_orchestrator,
    fake_writer,
    authenticated_browser,
    recording_broadcaster,
    session_factory,
) -> None:
    async with session_factory() as session:
        await VacancyRepository.create(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(
                    title="t",
                    apply_link="https://hh.ru/vacancy/1",
                    description="d",
                )
            ),
        )
        app = await ApplicationRepository.create(session=session, vacancy_id=1)
        app.status = ProcessingState.LETTER_SENDING
        await session.commit()
        app_id = app.id

    task = await start_consumer(
        fake_orchestrator,
        fake_writer,
        authenticated_browser,
        recording_broadcaster,
        session_factory,
    )
    try:
        await fake_orchestrator.enqueue(application_id=app_id)

        async def status_is_error() -> bool:
            async with session_factory() as s:
                a = await ApplicationRepository.get_by_id(
                    session=s, application_id=app_id
                )
                return a is not None and a.status == ProcessingState.ERROR

        await wait_until(status_is_error)
        assert fake_writer.calls == []
    finally:
        await stop_consumer(task)


async def test_pause_blocks_processing_until_resume(
    fake_orchestrator,
    fake_writer,
    authenticated_browser,
    recording_broadcaster,
    session_factory,
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)
    fake_orchestrator.pause()

    task = await start_consumer(
        fake_orchestrator,
        fake_writer,
        authenticated_browser,
        recording_broadcaster,
        session_factory,
    )
    try:
        await fake_orchestrator.enqueue(application_id=app_id)
        await asyncio.sleep(0.1)
        assert fake_writer.calls == []

        fake_orchestrator.resume()
        await asyncio.wait_for(fake_writer.invoked.wait(), timeout=2.0)
        assert len(fake_writer.calls) == 1
    finally:
        await stop_consumer(task)
