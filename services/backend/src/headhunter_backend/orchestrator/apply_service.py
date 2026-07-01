from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.subscribers import CallbackEventSubscriber
from headhunter_backend.core.events import VacancyWSEvent
from headhunter_backend.db.models import SettingsORM, VacancyORM
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.settings import SettingsRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.orchestrator.state_service import StateTransitionService


class AutoApplyService:
    """Turn a freshly parsed VacancyWSEvent into a PARSED → LETTER_PENDING
    application when auto_submit is enabled. The rest of the cascade
    (LLM generation, review, submit) is driven by LetterPendingWorker,
    AutoSubmitListener and LetterSendingWorker via the ApplicationWSEvent
    subscription chain — this service only owns the initial hand-off.
    """

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        state_service: StateTransitionService,
    ) -> None:
        self._session_maker = session_maker
        self._state_service = state_service
        self._log = get_logger(__name__)
        self._subscriber: CallbackEventSubscriber | None = None
        self._broadcaster: EventBroadcaster | None = None

    def start(self, broadcaster: EventBroadcaster) -> None:
        self._log.info("Starting service")
        self._subscriber = CallbackEventSubscriber.from_callback(
            lambda event: self._handle_event(event=event)
        )
        self._broadcaster = broadcaster
        broadcaster.register(self._subscriber)

    def stop(self) -> None:
        self._log.info("Terminating service")
        if self._broadcaster is not None and self._subscriber is not None:
            self._broadcaster.unregister(self._subscriber)
            self._subscriber = None

    async def _handle_event(self, event: BaseModel) -> None:
        try:
            if isinstance(event, VacancyWSEvent):
                await self._process(event=event)
        except Exception as e:
            self._log.error("Failed to handle event", error=str(e))

    async def _process(self, event: VacancyWSEvent) -> None:
        async with self._session_maker() as session:
            settings: SettingsORM = await SettingsRepository.get(session=session)
            if not settings.auto_submit:
                return
            vacancy_orm: VacancyORM | None = await VacancyRepository.get_by_apply_link(
                session=session, apply_link=event.data.apply_link
            )
            if vacancy_orm is None:
                self._log.error(
                    "Failed to find vacancy for VacancyWSEvent",
                    apply_link=event.data.apply_link,
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
            await self._state_service.transition_or_skip(
                session=session,
                application_id=application.id,
                event=ApplicationEvent.ENQUEUE_FOR_LETTER,
            )
