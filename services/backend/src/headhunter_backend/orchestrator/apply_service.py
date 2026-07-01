from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from headhunter_backend.api.events import VacancyWSEvent, ApplicationWSEvent
from headhunter_backend.api.schemas import ProcessingState
from headhunter_backend.db.models import SettingsORM, VacancyORM
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from headhunter_backend.exceptions import VacancyNotFoundError
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.db.converters import vacancy_to_schema
from headhunter_backend.orchestrator.queue import Orchestrator
from headhunter_backend.log import get_logger
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.subscribers import CallbackEventSubscriber
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.db.repositories.settings import SettingsRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository


class AutoApplyService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        ai_layer: AILayer,
        orchestrator: Orchestrator,
    ) -> None:
        self._session_maker: async_sessionmaker[AsyncSession] = session_maker
        self._ai_layer: AILayer = ai_layer
        self._orchestrator: Orchestrator = orchestrator
        self._log = get_logger(__name__)

    def start(self, broadcaster: EventBroadcaster) -> None:
        self._log.info("Starting service")
        self._subscriber = CallbackEventSubscriber.from_callback(
            lambda event: self._handle_event(event=event)
        )
        self._broadcaster: EventBroadcaster = broadcaster
        broadcaster.register(self._subscriber)

    def stop(self) -> None:
        self._log.info("Terminating service")
        self._broadcaster.unregister(self._subscriber)

    async def regenerate(self, vacancy_id: int) -> None:
        self._log.info("Requested to regenerate", vacancy_id=vacancy_id)
        async with self._session_maker() as session:
            vacancy_orm: VacancyORM | None = await VacancyRepository.get_by_id(
                session=session, vacancy_id=vacancy_id
            )
            if vacancy_orm is None:
                raise VacancyNotFoundError()
            await self._process(
                event=VacancyWSEvent(data=vacancy_to_schema(vacancy_orm))
            )

    async def _handle_event(self, event: BaseModel) -> None:
        self._log.info("Received event")
        if isinstance(event, VacancyWSEvent):
            self._log.info("Add to async queue to process event", payload=event)
            await self._process(event=event)
        elif isinstance(event, ApplicationWSEvent):
            if event.data.status == ProcessingState.LETTER_PENDING:
                try:
                    await self.regenerate(vacancy_id=event.data.vacancy_id)
                except VacancyNotFoundError as e:
                    self._log.error(
                        "Failed to regenerate",
                        vacancy_id=event.data.vacancy_id,
                        error=str(e),
                    )
        else:
            self._log.warn("Skip unsupported event", instance=type(event))

    async def _process(self, event: VacancyWSEvent) -> None:
        async with self._session_maker() as session:
            settings: SettingsORM = await SettingsRepository.get(session=session)
            vacancy_orm: VacancyORM | None = await VacancyRepository.get_by_apply_link(
                session=session, apply_link=event.data.apply_link
            )
            if not settings.auto_submit:
                self._log.info(
                    "Skip event since auto submittion is disabled", payload=event
                )
                return
            if vacancy_orm is None:
                self._log.error(
                    "Failed to find vacancy from DataBase for event", payload=event
                )
                return
            try:
                application = await ApplicationRepository.create(
                    session=session, vacancy_id=vacancy_orm.id
                )
            except IntegrityError:
                await session.rollback()
                self._log.info(
                    "Application already exists for vacancy, skipping",
                    vacancy_id=vacancy_orm.id,
                )
                return

            try:
                await ApplicationRepository.transition(
                    session=session,
                    application_id=application.id,
                    to_state=ApplicationEvent.ENQUEUE_FOR_LETTER,
                )
                result: AICoverLetterResult = (
                    await self._ai_layer.generate_cover_letter(
                        vacancy_model=vacancy_to_schema(row=vacancy_orm),
                        resume=settings.resume_text,
                        style=settings.letter_style,
                        system_prompt=settings.llm_system_prompt,
                    )
                )
                await CoverLetterRepository.create(
                    session=session, application_id=application.id, text=result.text
                )
                await ApplicationRepository.transition(
                    session=session,
                    application_id=application.id,
                    to_state=ApplicationEvent.LETTER_GENERATED,
                )
                # SUBMIT via ApplicationRepository (no broadcast) + explicit
                # LetterSendingWorker.enqueue — LetterSendingWorker will pick
                # the application up via its ApplicationWSEvent subscription
                # once apply_service is rewritten to broadcast in stage 4.3.
                await ApplicationRepository.transition(
                    session=session,
                    application_id=application.id,
                    to_state=ApplicationEvent.SUBMIT,
                )
                await self._orchestrator.enqueue(application_id=application.id)

            except Exception as e:
                self._log.error(
                    "Failed to process auto submition",
                    vacancy_id=vacancy_orm.id,
                    error=str(e),
                )
                await ApplicationRepository.transition(
                    session=session,
                    application_id=application.id,
                    to_state=ApplicationEvent.FAIL,
                    error_message=str(e),
                )
