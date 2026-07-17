from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.subscribers import CallbackEventSubscriber
from otklik_backend.core.events import ApplicationWSEvent
from otklik_backend.core.state import ProcessingState
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.log import get_logger
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService
from otklik_backend.orchestrator.workers.letter_sending import LetterSendingWorker


class AutoSubmitListener:
    def __init__(
        self,
        state_service: StateTransitionService,
        session_maker: async_sessionmaker[AsyncSession],
        broadcaster: EventBroadcaster,
        letter_sending_worker: LetterSendingWorker,
    ) -> None:
        self._state_service = state_service
        self._session_maker = session_maker
        self._broadcaster = broadcaster
        self._letter_sending_worker = letter_sending_worker
        self._log = get_logger(__name__)
        self._subscriber: CallbackEventSubscriber | None = None

    def start(self) -> None:
        subscriber = CallbackEventSubscriber.from_callback(
            lambda event: self._on_event(event=event)
        )
        self._broadcaster.register(subscriber)
        self._subscriber = subscriber

    def stop(self) -> None:
        if self._subscriber is not None:
            self._broadcaster.unregister(self._subscriber)
            self._subscriber = None

    async def _on_event(self, event: BaseModel) -> None:
        try:
            if not isinstance(event, ApplicationWSEvent):
                return
            if event.data.status != ProcessingState.LETTER_READY:
                return
            await self._maybe_submit(
                application_id=event.data.application_id,
                vacancy_id=event.data.vacancy_id,
            )
        except Exception as e:
            self._log.warning(
                "Failed to handle ApplicationWSEvent",
                error=str(e),
            )

    async def _maybe_submit(
        self, application_id: int, vacancy_id: int | None = None
    ) -> None:
        async with self._session_maker() as session:
            settings = await SettingsRepository.get(session=session)
            if not settings.auto_submit:
                return
            if self._letter_sending_worker.is_paused():
                self._log.info(
                    "Auto-submit skipped — letter-sending worker is paused",
                    application_id=application_id,
                    reason=self._letter_sending_worker.get_pause_reason(),
                )
                return
            await self._state_service.transition_or_skip(
                session=session,
                application_id=application_id,
                event=ApplicationEvent.SUBMIT,
            )

    async def recover(self, session: AsyncSession) -> int:
        settings = await SettingsRepository.get(session=session)
        if not settings.auto_submit:
            return 0
        if self._letter_sending_worker.is_paused():
            self._log.info(
                "Auto-submit recover skipped — letter-sending worker is paused",
                reason=self._letter_sending_worker.get_pause_reason(),
            )
            return 0
        pending = await ApplicationRepository.list_by_status(
            session=session, status=ProcessingState.LETTER_READY
        )
        for application in pending:
            await self._state_service.transition_or_skip(
                session=session,
                application_id=application.id,
                event=ApplicationEvent.SUBMIT,
            )
        return len(pending)
