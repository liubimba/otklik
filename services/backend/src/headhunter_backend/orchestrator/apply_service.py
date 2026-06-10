from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from headhunter_backend.api.events import VacancyWSEvent
from headhunter_backend.db.crud import (
    get_settings,
    get_vacancy_by_apply_link,
    create_application,
    transition_application,
    create_cover_letter,
)
from headhunter_backend.db.models import SettingsORM, VacancyORM, ApplicationORM
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.db.converters import vacancy_to_schema
from headhunter_backend.orchestrator.queue import Orchestrator
from headhunter_backend.log import get_logger
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.subscribers import CallbackEventSubscriber


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

    async def _handle_event(self, event: BaseModel) -> None:
        self._log.info("Received event")
        if isinstance(event, VacancyWSEvent):
            self._log.info("Add to async queue to process event", payload=event)
            await self._process(event=event)

    async def _process(self, event: VacancyWSEvent) -> None:
        async with self._session_maker() as session:
            settings: SettingsORM = await get_settings(session=session)
            vacancy_orm: VacancyORM | None = await get_vacancy_by_apply_link(
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
                application: ApplicationORM = await create_application(
                    session=session, vacancy_id=vacancy_orm.id
                )
                await transition_application(
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
                await create_cover_letter(
                    session=session, application_id=application.id, text=result.text
                )
                await transition_application(
                    session=session,
                    application_id=application.id,
                    to_state=ApplicationEvent.LETTER_GENERATED,
                )
                await transition_application(
                    session=session,
                    application_id=application.id,
                    to_state=ApplicationEvent.SUBMIT,
                )
                await self._orchestrator.enqueue(application_id=application.id)
            except IntegrityError:
                await session.rollback()
                self._log.info(
                    "Application already exists for vacancy, skipping",
                    vacancy_id=vacancy_orm.id,
                )
                return
            except Exception as e:
                self._log.error(
                    "Failed to process auto submition",
                    vacancy_id=vacancy_orm.id,
                    error=str(e),
                )
