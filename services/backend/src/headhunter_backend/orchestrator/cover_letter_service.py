import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from statemachine.exceptions import TransitionNotAllowed

from headhunter_backend.ai.exceptions import AILayerUnhealthyError
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.schemas import ProcessingState
from headhunter_backend.db.crud import (
    create_cover_letter,
    get_application_by_vacancy_id,
    get_settings,
    get_vacancy,
    list_applications_by_status,
)
from headhunter_backend.db.converters import vacancy_to_schema
from headhunter_backend.db.models import ApplicationORM, SettingsORM, VacancyORM
from headhunter_backend.exceptions import ApplicationNotFoundError, VacancyNotFoundError
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator._transitions import transition_and_broadcast
from headhunter_backend.orchestrator.state_machine import ApplicationEvent


class CoverLetterService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        ai_layer: AILayer,
        broadcaster: EventBroadcaster,
    ) -> None:
        self._session_maker = session_maker
        self._ai_layer = ai_layer
        self._broadcaster = broadcaster
        self._log = get_logger(__name__)
        # Holds references to fire-and-forget recovery tasks so they aren't GC'd before completion.
        self._tasks: set[asyncio.Task[None]] = set()

    async def regenerate(self, vacancy_id: int) -> AICoverLetterResult:
        if not (await self._ai_layer.get_health_status()).is_ready():
            raise AILayerUnhealthyError()
        async with self._session_maker() as session:
            vacancy_orm: VacancyORM | None = await get_vacancy(
                session=session, vacancy_id=vacancy_id
            )
            if vacancy_orm is None:
                raise VacancyNotFoundError()
            application: ApplicationORM | None = await get_application_by_vacancy_id(
                session=session, vacancy_id=vacancy_id
            )
            if application is None:
                raise ApplicationNotFoundError()
            settings: SettingsORM = await get_settings(session=session)
            cover_result: AICoverLetterResult = (
                await self._ai_layer.generate_cover_letter(
                    vacancy_model=vacancy_to_schema(vacancy_orm),
                    resume=settings.resume_text,
                    style=settings.letter_style,
                    system_prompt=settings.llm_system_prompt,
                )
            )
            await create_cover_letter(
                session=session,
                application_id=application.id,
                text=cover_result.text,
            )
            await transition_and_broadcast(
                session=session,
                broadcaster=self._broadcaster,
                application_id=application.id,
                to_state=ApplicationEvent.LETTER_GENERATED,
            )
            return cover_result

    async def recover_pending(self, session: AsyncSession) -> int:
        applications = await list_applications_by_status(
            session=session, status=ProcessingState.LETTER_PENDING
        )
        for application in applications:
            task = asyncio.create_task(
                self._safe_regenerate(vacancy_id=application.vacancy_id)
            )
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        if applications:
            self._log.info(
                "Scheduled letter regeneration for stuck applications",
                count=len(applications),
            )
        return len(applications)

    async def _safe_regenerate(self, vacancy_id: int) -> None:
        try:
            await self.regenerate(vacancy_id=vacancy_id)
        except TransitionNotAllowed:
            # Application moved out of LETTER_PENDING between scan and regenerate — recovery raced.
            self._log.warning(
                "Recovery skipped: application no longer in LETTER_PENDING",
                vacancy_id=vacancy_id,
            )
        except Exception as e:
            self._log.error(
                "Recovery regenerate failed",
                vacancy_id=vacancy_id,
                error=str(e),
            )
