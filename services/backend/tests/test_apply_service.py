import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.core.events import VacancyWSEvent
from headhunter_backend.api.schemas import ProcessingState, VacancyAPISchema
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.db.models import ApplicationORM, SettingsORM, VacancyORM
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.settings import SettingsRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.orchestrator.listeners.auto_apply import AutoApplyListener
from headhunter_backend.orchestrator.state_service import StateTransitionService


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


async def _seed_vacancy(
    session_factory: async_sessionmaker[AsyncSession], vacancy: VacancyAPISchema
) -> int:
    async with session_factory() as session:
        orm: VacancyORM = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy)
        )
        return orm.id


async def _make_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[AutoApplyListener, EventBroadcaster]:
    broadcaster = EventBroadcaster()
    state_service = StateTransitionService(broadcaster=broadcaster)
    service = AutoApplyListener(
        session_maker=session_factory,
        state_service=state_service,
        broadcaster=broadcaster,
    )
    service.start()
    return service, broadcaster


async def test_skips_when_auto_submit_disabled(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    vacancy_id: int = await _seed_vacancy(session_factory, vacancy_model)
    service, broadcaster = await _make_service(session_factory)

    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    async with session_factory() as session:
        application: (
            ApplicationORM | None
        ) = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=vacancy_id
        )

    assert application is None


async def test_skips_when_vacancy_not_in_db(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    await _enable_auto_submit(session_factory)
    service, broadcaster = await _make_service(session_factory)

    # publish without seeding vacancy in DB
    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    async with session_factory() as session:
        assert await ApplicationRepository.list_active(session=session) == []


async def test_happy_path_creates_application_and_enqueues_for_letter(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    vacancy_id: int = await _seed_vacancy(session_factory, vacancy_model)
    await _enable_auto_submit(session_factory)

    service, broadcaster = await _make_service(session_factory)

    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    async with session_factory() as session:
        application: (
            ApplicationORM | None
        ) = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=vacancy_id
        )
        assert application is not None
        # apply_service hands off to LetterPendingWorker via the LETTER_PENDING
        # ApplicationWSEvent — no LLM call here. Post-refactor apply_service
        # only owns PARSED → LETTER_PENDING.
        assert application.status == ProcessingState.LETTER_PENDING


async def test_silently_skips_when_application_already_exists(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    vacancy_id: int = await _seed_vacancy(session_factory, vacancy_model)
    await _enable_auto_submit(session_factory)

    async with session_factory() as session:
        await ApplicationRepository.create(session=session, vacancy_id=vacancy_id)

    service, broadcaster = await _make_service(session_factory)

    # Should not raise — second create_application would hit UNIQUE(vacancy_id).
    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    async with session_factory() as session:
        application: (
            ApplicationORM | None
        ) = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=vacancy_id
        )
        # Existing application untouched, status still PARSED (from create_application).
        assert application is not None
        assert application.status == ProcessingState.PARSED


async def test_ignores_non_vacancy_events(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    await _seed_vacancy(session_factory, vacancy_model)
    await _enable_auto_submit(session_factory)

    service, broadcaster = await _make_service(session_factory)

    from headhunter_backend.core.events import SearchData, SearchWSEvent

    await broadcaster.publish(
        event=SearchWSEvent(
            data=SearchData(
                search_id="x", parsed_vacancies=1, parsed_pages=0, status="running"
            )
        )
    )
    await _drain(broadcaster)

    async with session_factory() as session:
        assert await ApplicationRepository.list_active(session=session) == []
