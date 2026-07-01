import asyncio
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.ai.health import AILayerHealthStatus
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.schemas import ProcessingState, VacancyAPISchema
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.db.models import SettingsORM
from headhunter_backend.orchestrator.cover_letter_service import CoverLetterService
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.settings import SettingsRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository

from tests.conftest import wait_until


def _ok_result(text: str = "Generated") -> AICoverLetterResult:
    return AICoverLetterResult(
        text=text,
        model_used="test/model",
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        was_fallback=False,
    )


def _ready_ai_layer(result: AICoverLetterResult) -> AILayer:
    layer = AILayer(deployments=[])
    layer.get_health_status = AsyncMock(return_value=AILayerHealthStatus.HEALTHY)  # type: ignore[assignment]
    layer.generate_cover_letter = AsyncMock(return_value=result)  # type: ignore[assignment]
    return layer


async def _seed_pending(
    session_factory: async_sessionmaker[AsyncSession], apply_link: str
) -> int:
    vacancy = VacancyAPISchema(
        title="V",
        apply_link=apply_link,
        description="d",
    )
    async with session_factory() as session:
        orm = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(vacancy)
        )
        app = await ApplicationRepository.create(session=session, vacancy_id=orm.id)
        await ApplicationRepository.transition(
            session=session,
            application_id=app.id,
            to_state=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )
        return orm.id


async def _set_resume_and_style(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        settings: SettingsORM = await SettingsRepository.get(session=session)
        settings.resume_text = "resume"
        settings.letter_style = "polite"
        await SettingsRepository.update(session=session, new_settings=settings)


async def test_recover_pending_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_resume_and_style(session_factory)
    v1 = await _seed_pending(session_factory, "https://hh.ru/v/1")
    v2 = await _seed_pending(session_factory, "https://hh.ru/v/2")

    ai_layer = _ready_ai_layer(_ok_result(text="hello"))
    broadcaster = EventBroadcaster()
    service = CoverLetterService(
        session_maker=session_factory,
        ai_layer=ai_layer,
        broadcaster=broadcaster,
    )

    async with session_factory() as session:
        scheduled = await service.recover_pending(session=session)
    assert scheduled == 2

    async def both_drained() -> bool:
        async with session_factory() as session:
            pending = await ApplicationRepository.list_by_status(
                session=session, status=ProcessingState.LETTER_PENDING
            )
            return len(pending) == 0

    await wait_until(both_drained, timeout=2.0)

    async with session_factory() as session:
        app1 = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=v1
        )
        app2 = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=v2
        )
        assert app1 is not None and app1.status == ProcessingState.LETTER_READY
        assert app2 is not None and app2.status == ProcessingState.LETTER_READY

    assert ai_layer.generate_cover_letter.await_count == 2  # type: ignore[attr-defined]

    # Second call finds nothing left in LETTER_PENDING — no new tasks scheduled.
    async with session_factory() as session:
        scheduled_again = await service.recover_pending(session=session)
    assert scheduled_again == 0
    assert ai_layer.generate_cover_letter.await_count == 2  # type: ignore[attr-defined]


async def test_recover_pending_swallows_transition_race(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_resume_and_style(session_factory)
    vacancy_id = await _seed_pending(session_factory, "https://hh.ru/race")

    # Simulate someone advancing the application out of LETTER_PENDING right before recovery picks it up.
    async with session_factory() as session:
        app = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=vacancy_id
        )
        assert app is not None
        await ApplicationRepository.transition(
            session=session,
            application_id=app.id,
            to_state=ApplicationEvent.LETTER_GENERATED,
        )
        await ApplicationRepository.transition(
            session=session,
            application_id=app.id,
            to_state=ApplicationEvent.SUBMIT,
        )

    ai_layer = _ready_ai_layer(_ok_result())
    broadcaster = EventBroadcaster()
    service = CoverLetterService(
        session_maker=session_factory,
        ai_layer=ai_layer,
        broadcaster=broadcaster,
    )

    # Manually queue regenerate even though the application has moved on.
    # The state transition LETTER_SENDING → LETTER_GENERATED is not allowed; recovery must swallow.
    task = asyncio.create_task(service._safe_regenerate(vacancy_id=vacancy_id))
    await task  # must not raise

    async with session_factory() as session:
        app = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=vacancy_id
        )
        assert app is not None
        assert app.status == ProcessingState.LETTER_SENDING
