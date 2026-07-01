from headhunter_backend.orchestrator.workers.letter_sending import LetterSendingWorker
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.api.schemas import ProcessingState, VacancyAPISchema
from tests.conftest import (
    FakeWriter,
    FakeBrowser,
    RecordingBroadcaster,
    wait_until,
)

import asyncio

from headhunter_backend.core.site.result import SubmissionResult
from headhunter_backend.db.models import RateLimitEventORM
from headhunter_backend.core.events import CaptchaWSEvent, ApplicationWSEvent
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from sqlalchemy import select, func


async def test_recover_picks_up_letter_sending_only(
    fake_orchestrator: LetterSendingWorker,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """LetterSendingWorker.recover() must enqueue only apps whose status matches
    handled_status (LETTER_SENDING). Apps stuck in other statuses belong to a
    different worker's recover() and must be ignored here."""
    picked: list[int] = []
    async with session_factory() as session:
        for index in range(4):
            await VacancyRepository.create(
                session=session,
                vacancy=vacancy_to_orm(
                    VacancyAPISchema(
                        title="t", apply_link=f"link{index}", description="d"
                    )
                ),
            )

        for vacancy_id, status in (
            (1, ProcessingState.LETTER_SENDING),
            (2, ProcessingState.LETTER_SENDING),
            (3, ProcessingState.LETTER_SENT),
            (4, ProcessingState.SKIPPED),
        ):
            app = await ApplicationRepository.create(
                session=session, vacancy_id=vacancy_id
            )
            app.status = status
            if status == ProcessingState.LETTER_SENDING:
                picked.append(app.id)
        await session.commit()

        recovered = await fake_orchestrator.recover(session=session)
        assert recovered == len(picked)
        assert fake_orchestrator.qsize() == len(picked)
        drained = {
            await fake_orchestrator.get_next(),
            await fake_orchestrator.get_next(),
        }
        assert drained == set(picked)
        assert fake_orchestrator.qsize() == 0


async def test_enqueue_then_get_next(fake_orchestrator: LetterSendingWorker) -> None:
    await fake_orchestrator.enqueue(application_id=42)
    assert fake_orchestrator.qsize() == 1
    next_id: int = await fake_orchestrator.get_next()
    assert next_id == 42
    assert fake_orchestrator.qsize() == 0


# ─ хелпер: вакансия + заявка сразу в LETTER_SENDING + письмо ─────────
async def seed_app_in_letter_sending(
    session_factory: async_sessionmaker[AsyncSession],
    apply_link: str = "https://hh.ru/vacancy/1",
    response_link: str = "https://hh.ru/applicant/vacancy_response?vacancyId=1",
) -> int:
    async with session_factory() as session:
        await VacancyRepository.create(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(
                    title="t",
                    apply_link=apply_link,
                    response_link=response_link,
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


# ─ хелпер: стартовать run() как фоновую задачу ───────────────────
async def start_consumer(
    orchestrator: LetterSendingWorker,
    writer: FakeWriter,  # kept in signature so callsites don't have to change
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


# ─ Тесты ─────────────────────────────────────────────────────────────


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

        # log_submission записал строку в rate_limits
        async with session_factory() as s:
            count = (
                await s.execute(select(func.count(RateLimitEventORM.id)))
            ).scalar_one()
            assert count == 1

        # событие SubmissionEvent(succeeded=True)
        submissions = [
            e for e in recording_broadcaster.events if isinstance(e, ApplicationWSEvent)
        ]
        assert len(submissions) == 1
        assert submissions[0].data.status is ProcessingState.LETTER_SENT
        assert submissions[0].data.application_id == app_id
    finally:
        await stop_consumer(task)


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

        # ждём пока writer успеет быть вызван
        await asyncio.wait_for(fake_writer.invoked.wait(), timeout=2.0)
        # дать consumer'у дойти до pause() + re-enqueue
        await wait_until(
            lambda: fake_orchestrator.is_paused() and fake_orchestrator.qsize() == 1
        )

        # статус заявки НЕ изменился (всё ещё LETTER_SENDING)
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
    """Regression: after a NOT_AUTHORIZED gate result the worker paused
    itself and stayed paused until the user hit /system/orchestrator/resume
    by hand — a hidden step. Now the worker listens for AuthWSEvent and
    auto-resumes when auth is restored.

    Drive the pause + event flow directly (no session/queue seeding) —
    this test asserts the listener wiring in isolation. Because the
    broadcaster delivers events fire-and-forget via asyncio.create_task
    the assertion is wrapped in `wait_until`."""
    from headhunter_backend.api.schemas import AuthStatusAPISchema
    from headhunter_backend.core.events import AuthWSEvent

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
    """AuthWSEvent(unauthorized) or (authorizing) must not touch the pause
    state — only a successful re-auth clears the block."""
    from headhunter_backend.api.schemas import AuthStatusAPISchema
    from headhunter_backend.core.events import AuthWSEvent

    fake_orchestrator.start()
    try:
        fake_orchestrator.pause(reason=fake_orchestrator.PAUSE_REASON_NOT_AUTHORIZED)
        for status in (
            AuthStatusAPISchema.unauthorized(),
            AuthStatusAPISchema.authorizing(),
        ):
            await recording_broadcaster.publish(event=AuthWSEvent(data=status))
        # Give delivery tasks a chance to run.
        await asyncio.sleep(0.05)
        assert fake_orchestrator.is_paused()
    finally:
        fake_orchestrator.stop()


async def test_worker_does_not_auto_resume_when_paused_for_other_reason(
    fake_orchestrator: LetterSendingWorker,
    recording_broadcaster: RecordingBroadcaster,
) -> None:
    """Captcha pauses (and any future pause reasons) must not be lifted by
    the auth listener — they need their own resume path."""
    from headhunter_backend.api.schemas import AuthStatusAPISchema
    from headhunter_backend.core.events import AuthWSEvent

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
    """Sanity: incoming AuthWSEvent while the worker is running normally
    shouldn't call resume() and shouldn't panic."""
    from headhunter_backend.api.schemas import AuthStatusAPISchema
    from headhunter_backend.core.events import AuthWSEvent

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
    # fake_browser остаётся unauthorized
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

        # Writer не должен был вызываться
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

    # Забить hourly-лимит (default 5).
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
                    response_link="https://hh.ru/applicant/vacancy_response?vacancyId=1",
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
        # consumer стоит на _resume_event.wait()
        assert fake_writer.calls == []

        fake_orchestrator.resume()
        await asyncio.wait_for(fake_writer.invoked.wait(), timeout=2.0)
        assert len(fake_writer.calls) == 1
    finally:
        await stop_consumer(task)
