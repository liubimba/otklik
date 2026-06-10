from headhunter_backend.orchestrator.queue import Orchestrator
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from headhunter_backend.db.models import ApplicationORM
from headhunter_backend.db.crud import create_application, create_vacancy
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.api.schemas import ProcessingState, VacancyAPISchema
from tests.conftest import (
    FakeWriter,
    FakeBrowser,
    RecordingBroadcaster,
    wait_until,
)

import asyncio

from headhunter_backend.browser.writer import SubmitResult
from headhunter_backend.browser.selectors import HHRU_SELECTORS
from headhunter_backend.db.crud import (
    create_cover_letter,
    get_application_by_id,
)
from headhunter_backend.db.models import RateLimitEventORM
from headhunter_backend.api.events import CaptchaWSEvent, ApplicationWSEvent
from sqlalchemy import select, func


async def test_recover_from_db_pushes_applications(
    fake_orchestrator: Orchestrator, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    applications: list[ApplicationORM] = []
    async with session_factory() as session:
        for _ in range(4):
            await create_vacancy(
                session=session,
                vacancy=vacancy_to_orm(
                    VacancyAPISchema(
                        title="test", apply_link=f"test{_}", description="test"
                    )
                ),
            )

        applications.append(await create_application(session=session, vacancy_id=1))
        applications.append(await create_application(session=session, vacancy_id=2))

        application: ApplicationORM = await create_application(
            session=session, vacancy_id=3
        )
        application.status = ProcessingState.LETTER_SENT
        await session.commit()

        application: ApplicationORM = await create_application(
            session=session, vacancy_id=4
        )
        application.status = ProcessingState.SKIPPED
        await session.commit()

        recovered_count: int = await fake_orchestrator.recover_from_db(session=session)
        assert recovered_count == len(applications)
        assert fake_orchestrator.qsize() == len(applications)
        assert {
            await fake_orchestrator.get_next(),
            await fake_orchestrator.get_next(),
        } == {applications[0].id, applications[1].id}
        assert fake_orchestrator.qsize() == 0


async def test_enqueue_then_get_next(fake_orchestrator: Orchestrator) -> None:
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
        await create_vacancy(
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
        app = await create_application(session=session, vacancy_id=1)
        app.status = ProcessingState.LETTER_SENDING
        await create_cover_letter(session=session, application_id=app.id, text="hi")
        await session.commit()
        return app.id


# ─ хелпер: стартовать consume() как фоновую задачу ───────────────────
async def start_consumer(
    orchestrator: Orchestrator,
    writer: FakeWriter,
    browser: FakeBrowser,
    broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> asyncio.Task:
    return asyncio.create_task(
        orchestrator.consume(
            writer=writer,
            session_maker=session_factory,
            browser=browser,
            broadcaster=broadcaster,
            selectors=HHRU_SELECTORS,
        )
    )


async def stop_consumer(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ─ Тесты ─────────────────────────────────────────────────────────────


async def test_consume_submitted_transitions_and_logs(
    fake_orchestrator: Orchestrator,
    fake_writer: FakeWriter,
    authenticated_browser: FakeBrowser,
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app_id = await seed_app_in_letter_sending(session_factory)
    fake_writer.queue(SubmitResult.submitted())

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
                app = await get_application_by_id(session=s, application_id=app_id)
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
    fake_writer.queue(SubmitResult.failed(reason="boom"))

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
                app = await get_application_by_id(session=s, application_id=app_id)
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
    fake_writer.queue(SubmitResult.captcha())

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
            app = await get_application_by_id(session=s, application_id=app_id)
            assert app is not None
            assert app.status == ProcessingState.LETTER_SENDING

        captchas = [
            e for e in recording_broadcaster.events if isinstance(e, CaptchaWSEvent)
        ]
        assert len(captchas) == 1
        assert captchas[0].data.application_id == app_id
    finally:
        await stop_consumer(task)


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
                app = await get_application_by_id(session=s, application_id=app_id)
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
            app = await get_application_by_id(session=s, application_id=app_id)
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
        await create_vacancy(
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
        app = await create_application(session=session, vacancy_id=1)
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
                a = await get_application_by_id(session=s, application_id=app_id)
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
