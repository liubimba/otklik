from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.ai.result import AICoverLetterResult
from otklik_backend.ai.source_tools import LLMSource
from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.models import ApplicationORM
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.orchestrator.cover_letter_service import CoverLetterService
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService


class RecordingAILayer:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def generate_cover_letter(self, **kwargs: Any) -> AICoverLetterResult:
        self.calls.append(kwargs)
        return AICoverLetterResult(
            text="letter",
            model_used="fake-model",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            was_fallback=False,
        )


class FakeContextSourceService:
    def __init__(self, sources: list[LLMSource]) -> None:
        self._sources = sources

    async def list_ok_for_llm(self) -> list[LLMSource]:
        return self._sources


async def _seed_application(
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


async def test_regenerate_passes_ok_sources_to_ai_layer(
    session_factory: async_sessionmaker[AsyncSession],
    fake_state_service: StateTransitionService,
    vacancy_model: VacancyAPISchema,
) -> None:
    vacancy_id, _ = await _seed_application(session_factory, vacancy_model)
    ai_layer = RecordingAILayer()
    sources = [
        LLMSource(
            id=1, label="One", description="d1", url="https://a", content="a-content"
        ),
        LLMSource(
            id=2, label="Two", description=None, url="https://b", content="b-content"
        ),
    ]
    context_source_service = FakeContextSourceService(sources)
    service = CoverLetterService(
        session_maker=session_factory,
        ai_layer=ai_layer,  # type: ignore[arg-type]
        state_service=fake_state_service,
        context_source_service=context_source_service,  # type: ignore[arg-type]
    )

    await service.regenerate(vacancy_id)

    assert len(ai_layer.calls) == 1
    passed_sources = ai_layer.calls[0]["sources"]
    assert passed_sources == sources
