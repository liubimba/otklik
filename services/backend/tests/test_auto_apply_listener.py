import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.schemas import ProcessingState, VacancyAPISchema
from otklik_backend.core.events import VacancyWSEvent
from otklik_backend.core.state import ErrorDomain
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.models import ApplicationORM, CoverLetterORM, SettingsORM
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.orchestrator.listeners.auto_apply import AutoApplyListener
from otklik_backend.orchestrator.state_service import StateTransitionService


async def _drain(broadcaster: EventBroadcaster) -> None:
    while broadcaster._pending:
        pending = list(broadcaster._pending)
        await asyncio.gather(*pending, return_exceptions=True)


async def _set_flags(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    auto_generate: bool,
    auto_submit: bool,
) -> None:
    async with session_factory() as session:
        settings: SettingsORM = await SettingsRepository.get(session=session)
        settings.auto_generate = auto_generate
        settings.auto_submit = auto_submit
        await SettingsRepository.update(session=session, new_settings=settings)


async def _seed_vacancy(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy: VacancyAPISchema,
) -> int:
    async with session_factory() as session:
        await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy)
        )
        stored = await VacancyRepository.get_by_apply_link(
            session=session, apply_link=vacancy.apply_link
        )
        assert stored is not None
        return stored.id


async def _seed_application(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_id: int,
    status: ProcessingState,
    error_domain: ErrorDomain | None = None,
    with_letter: bool = False,
) -> int:
    async with session_factory() as session:
        application = ApplicationORM(
            vacancy_id=vacancy_id, status=status, error_domain=error_domain
        )
        session.add(application)
        await session.commit()
        application_id = application.id
        if with_letter:
            session.add(
                CoverLetterORM(application_id=application_id, text="existing letter")
            )
            await session.commit()
        return application_id


async def test_auto_apply_generates_when_auto_generate_on_even_if_auto_submit_off(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=True, auto_submit=False)
    await _seed_vacancy(session_factory, vacancy_model)

    listener = AutoApplyListener(
        session_maker=session_factory,
        state_service=fake_state_service,
        broadcaster=recording_broadcaster,
    )
    listener.start()

    await recording_broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(recording_broadcaster)

    async with session_factory() as session:
        apps = await ApplicationRepository.list_all(session=session)
        assert len(apps) == 1


async def test_auto_apply_does_nothing_when_auto_generate_off(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=False, auto_submit=True)
    await _seed_vacancy(session_factory, vacancy_model)

    listener = AutoApplyListener(
        session_maker=session_factory,
        state_service=fake_state_service,
        broadcaster=recording_broadcaster,
    )
    listener.start()

    await recording_broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(recording_broadcaster)

    async with session_factory() as session:
        apps = await ApplicationRepository.list_all(session=session)
        assert len(apps) == 0


async def test_auto_apply_marks_already_applied_and_skips_the_flow(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=True, auto_submit=True)
    await _seed_vacancy(session_factory, vacancy_model)

    listener = AutoApplyListener(
        session_maker=session_factory,
        state_service=fake_state_service,
        broadcaster=recording_broadcaster,
    )
    listener.start()

    responded = vacancy_model.model_copy(update={"already_responded": True})
    await recording_broadcaster.publish(event=VacancyWSEvent(data=responded))
    await _drain(recording_broadcaster)

    async with session_factory() as session:
        apps = await ApplicationRepository.list_all(session=session)
        assert len(apps) == 1
        assert apps[0].status == ProcessingState.ALREADY_APPLIED


async def _publish_and_drain(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    listener = AutoApplyListener(
        session_maker=session_factory,
        state_service=fake_state_service,
        broadcaster=recording_broadcaster,
    )
    listener.start()
    await recording_broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(recording_broadcaster)


async def test_auto_apply_regenerates_a_reparsed_interrupted_vacancy_without_letter(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=True, auto_submit=False)
    vacancy_id = await _seed_vacancy(session_factory, vacancy_model)
    app_id = await _seed_application(
        session_factory, vacancy_id, ProcessingState.INTERRUPTED
    )

    await _publish_and_drain(
        session_factory, vacancy_model, recording_broadcaster, fake_state_service
    )

    async with session_factory() as session:
        app = await ApplicationRepository.get_by_id(
            session=session, application_id=app_id
        )
        assert app is not None
        assert app.status == ProcessingState.LETTER_PENDING


async def test_auto_apply_requeues_a_reparsed_submission_error(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=True, auto_submit=True)
    vacancy_id = await _seed_vacancy(session_factory, vacancy_model)
    app_id = await _seed_application(
        session_factory,
        vacancy_id,
        ProcessingState.ERROR,
        error_domain=ErrorDomain.SUBMISSION,
        with_letter=True,
    )

    await _publish_and_drain(
        session_factory, vacancy_model, recording_broadcaster, fake_state_service
    )

    async with session_factory() as session:
        app = await ApplicationRepository.get_by_id(
            session=session, application_id=app_id
        )
        assert app is not None
        assert app.status == ProcessingState.LETTER_QUEUED


async def test_auto_apply_leaves_a_reparsed_sent_vacancy_untouched(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
    recording_broadcaster: EventBroadcaster,
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=True, auto_submit=True)
    vacancy_id = await _seed_vacancy(session_factory, vacancy_model)
    app_id = await _seed_application(
        session_factory, vacancy_id, ProcessingState.LETTER_SENT
    )

    await _publish_and_drain(
        session_factory, vacancy_model, recording_broadcaster, fake_state_service
    )

    async with session_factory() as session:
        app = await ApplicationRepository.get_by_id(
            session=session, application_id=app_id
        )
        assert app is not None
        assert app.status == ProcessingState.LETTER_SENT
        apps = await ApplicationRepository.list_all(session=session)
        assert len(apps) == 1
