import asyncio
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.ai.exceptions import GenerationCoverLetterError
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.events import VacancyWSEvent
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.db.models import (
    ApplicationORM,
    CoverLetterORM,
    SettingsORM,
    VacancyORM,
)
from headhunter_backend.api.schemas import ProcessingState, VacancyAPISchema
from headhunter_backend.orchestrator.apply_service import AutoApplyService
from headhunter_backend.orchestrator.queue import Orchestrator
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.db.repositories.settings import SettingsRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository


async def _drain(broadcaster: EventBroadcaster) -> None:
    """Wait for broadcaster's fire-and-forget delivery tasks to finish."""
    while broadcaster._pending:
        pending = list(broadcaster._pending)
        await asyncio.gather(*pending, return_exceptions=True)


def _ok_result(text: str = "Generated letter") -> AICoverLetterResult:
    return AICoverLetterResult(
        text=text,
        model_used="test/model",
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        was_fallback=False,
    )


def _make_ai_layer(result: AICoverLetterResult | Exception) -> AILayer:
    layer = AILayer(deployments=[])
    mock = AsyncMock()
    if isinstance(result, Exception):
        mock.side_effect = result
    else:
        mock.return_value = result
    layer.generate_cover_letter = mock  # type: ignore[assignment]
    return layer


async def _enable_auto_submit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        settings: SettingsORM = await SettingsRepository.get(session=session)
        settings.auto_submit = True
        settings.resume_text = "resume body"
        settings.letter_style = "polite"
        await SettingsRepository.update(session=session, new_settings=settings)


async def _seed_vacancy(
    session_factory: async_sessionmaker[AsyncSession], vacancy: VacancyAPISchema
) -> int:
    async with session_factory() as session:
        orm: VacancyORM = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy)
        )
        return orm.id


class _StubOrchestrator:
    def __init__(self) -> None:
        self._pending: list[int] = []

    async def enqueue(self, application_id: int) -> None:
        self._pending.append(application_id)

    def qsize(self) -> int:
        return len(self._pending)

    def get_application_ids(self) -> list[int]:
        return list(self._pending)


async def _make_service_and_broadcast(
    session_factory: async_sessionmaker[AsyncSession],
    ai_layer: AILayer,
    orchestrator: Orchestrator | None = None,
) -> tuple[AutoApplyService, EventBroadcaster, Orchestrator]:
    broadcaster = EventBroadcaster()
    orch = orchestrator or _StubOrchestrator()  # type: ignore[assignment]
    service = AutoApplyService(
        session_maker=session_factory,
        ai_layer=ai_layer,
        orchestrator=orch,
    )
    service.start(broadcaster=broadcaster)
    return service, broadcaster, orch


async def test_skips_when_auto_submit_disabled(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    vacancy_id: int = await _seed_vacancy(session_factory, vacancy_model)
    ai_layer = _make_ai_layer(_ok_result())
    service, broadcaster, orch = await _make_service_and_broadcast(
        session_factory, ai_layer
    )

    # auto_submit is False by default; do NOT enable it
    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    async with session_factory() as session:
        application: (
            ApplicationORM | None
        ) = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=vacancy_id
        )

    assert application is None
    ai_layer.generate_cover_letter.assert_not_called()  # type: ignore[attr-defined]
    assert orch.qsize() == 0


async def test_skips_when_vacancy_not_in_db(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    await _enable_auto_submit(session_factory)
    ai_layer = _make_ai_layer(_ok_result())
    service, broadcaster, orch = await _make_service_and_broadcast(
        session_factory, ai_layer
    )

    # publish without seeding vacancy in DB
    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    ai_layer.generate_cover_letter.assert_not_called()  # type: ignore[attr-defined]
    assert orch.qsize() == 0


async def test_happy_path_creates_application_letter_and_enqueues(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    vacancy_id: int = await _seed_vacancy(session_factory, vacancy_model)
    await _enable_auto_submit(session_factory)

    ai_layer = _make_ai_layer(_ok_result(text="Hello there"))
    service, broadcaster, orch = await _make_service_and_broadcast(
        session_factory, ai_layer
    )

    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    async with session_factory() as session:
        application: (
            ApplicationORM | None
        ) = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=vacancy_id
        )
        assert application is not None
        assert application.status == ProcessingState.LETTER_SENDING, (
            "AutoApply must transition LETTER_READY → LETTER_SENDING before enqueue, "
            "otherwise Orchestrator._process_one will skip the application"
        )

        letter: (
            CoverLetterORM | None
        ) = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=application.id
        )
        assert letter is not None
        assert letter.text == "Hello there"

    ai_layer.generate_cover_letter.assert_awaited_once()  # type: ignore[attr-defined]
    assert orch.qsize() == 1
    assert list(orch.get_application_ids()) == [application.id]


async def test_ai_failure_leaves_application_in_letter_pending(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    vacancy_id: int = await _seed_vacancy(session_factory, vacancy_model)
    await _enable_auto_submit(session_factory)

    ai_layer = _make_ai_layer(GenerationCoverLetterError("no deployments"))
    service, broadcaster, orch = await _make_service_and_broadcast(
        session_factory, ai_layer
    )

    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    async with session_factory() as session:
        application: (
            ApplicationORM | None
        ) = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=vacancy_id
        )
        assert application is not None
        assert application.status == ProcessingState.LETTER_PENDING

        letter: (
            CoverLetterORM | None
        ) = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=application.id
        )
        assert letter is None

    assert orch.qsize() == 0


async def test_silently_skips_when_application_already_exists(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    """Manual flow already created an application for this vacancy.
    AutoApply must silently no-op, not raise IntegrityError up."""
    vacancy_id: int = await _seed_vacancy(session_factory, vacancy_model)
    await _enable_auto_submit(session_factory)

    async with session_factory() as session:
        await ApplicationRepository.create(session=session, vacancy_id=vacancy_id)

    ai_layer = _make_ai_layer(_ok_result())
    service, broadcaster, orch = await _make_service_and_broadcast(
        session_factory, ai_layer
    )

    # Should not raise — second create_application would hit UNIQUE(vacancy_id).
    await broadcaster.publish(event=VacancyWSEvent(data=vacancy_model))
    await _drain(broadcaster)

    ai_layer.generate_cover_letter.assert_not_called()  # type: ignore[attr-defined]
    assert orch.qsize() == 0

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
    """AutoApply must filter events by type — SearchWSEvent etc. should be no-ops."""
    await _seed_vacancy(session_factory, vacancy_model)
    await _enable_auto_submit(session_factory)

    ai_layer = _make_ai_layer(_ok_result())
    service, broadcaster, orch = await _make_service_and_broadcast(
        session_factory, ai_layer
    )

    from headhunter_backend.api.events import SearchData, SearchWSEvent

    await broadcaster.publish(
        event=SearchWSEvent(
            data=SearchData(
                search_id="x", parsed_vacancies=1, parsed_pages=0, status="running"
            )
        )
    )
    await _drain(broadcaster)

    ai_layer.generate_cover_letter.assert_not_called()  # type: ignore[attr-defined]
    assert orch.qsize() == 0
