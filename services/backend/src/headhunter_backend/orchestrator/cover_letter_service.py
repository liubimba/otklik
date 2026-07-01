from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from headhunter_backend.ai.exceptions import AILayerUnhealthyError
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.db.converters import vacancy_to_schema
from headhunter_backend.db.models import ApplicationORM, SettingsORM, VacancyORM
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.db.repositories.settings import SettingsRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.exceptions import ApplicationNotFoundError, VacancyNotFoundError
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.orchestrator.state_service import StateTransitionService


class CoverLetterService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        ai_layer: AILayer,
        state_service: StateTransitionService,
    ) -> None:
        self._session_maker = session_maker
        self._ai_layer = ai_layer
        self._state_service = state_service
        self._log = get_logger(__name__)

    async def regenerate(self, vacancy_id: int) -> AICoverLetterResult:
        if not (await self._ai_layer.get_health_status()).is_ready():
            raise AILayerUnhealthyError()
        async with self._session_maker() as session:
            vacancy_orm: VacancyORM | None = await VacancyRepository.get_by_id(
                session=session, vacancy_id=vacancy_id
            )
            if vacancy_orm is None:
                raise VacancyNotFoundError()
            application: (
                ApplicationORM | None
            ) = await ApplicationRepository.get_by_vacancy_id(
                session=session, vacancy_id=vacancy_id
            )
            if application is None:
                raise ApplicationNotFoundError()
            settings: SettingsORM = await SettingsRepository.get(session=session)
            cover_result: AICoverLetterResult = (
                await self._ai_layer.generate_cover_letter(
                    vacancy_model=vacancy_to_schema(vacancy_orm),
                    resume=settings.resume_text,
                    style=settings.letter_style,
                    system_prompt=settings.llm_system_prompt,
                )
            )
            await CoverLetterRepository.create(
                session=session,
                application_id=application.id,
                text=cover_result.text,
            )
            await self._state_service.transition(
                session=session,
                application_id=application.id,
                event=ApplicationEvent.LETTER_GENERATED,
            )
            return cover_result
