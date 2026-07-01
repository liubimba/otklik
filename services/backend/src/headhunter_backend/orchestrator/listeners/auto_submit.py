from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.subscribers import CallbackEventSubscriber
from headhunter_backend.core.events import ApplicationWSEvent
from headhunter_backend.core.state import ProcessingState
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.settings import SettingsRepository
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.orchestrator.state_service import StateTransitionService


class AutoSubmitListener:
    def __init__(
        self,
        state_service: StateTransitionService,
        session_maker: async_sessionmaker[AsyncSession],
        broadcaster: EventBroadcaster,
    ) -> None:
        self._state_service = state_service
        self._session_maker = session_maker
        self._broadcaster = broadcaster
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
            await self._state_service.transition_or_skip(
                session=session,
                application_id=application_id,
                event=ApplicationEvent.SUBMIT,
            )

    async def recover(self, session: AsyncSession) -> int:
        # Crash-after-LETTER_READY orphans: rescan on startup and re-emit SUBMIT
        # if auto_submit is on. Otherwise the app would sit forever waiting for
        # the WS event we already missed.
        settings = await SettingsRepository.get(session=session)
        if not settings.auto_submit:
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
