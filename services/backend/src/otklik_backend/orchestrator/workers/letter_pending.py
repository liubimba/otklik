import asyncio

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.subscribers import CallbackEventSubscriber
from otklik_backend.core.events import ApplicationWSEvent
from otklik_backend.core.state import ProcessingState
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.orchestrator.cover_letter_service import CoverLetterService
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService
from otklik_backend.orchestrator.workers.base import Worker


class LetterPendingWorker(Worker):
    handled_status = ProcessingState.LETTER_PENDING

    def __init__(
        self,
        cover_letter_service: CoverLetterService,
        state_service: StateTransitionService,
        session_maker: async_sessionmaker[AsyncSession],
        broadcaster: EventBroadcaster,
    ) -> None:
        super().__init__()
        self._cover_letter_service = cover_letter_service
        self._state_service = state_service
        self._session_maker = session_maker
        self._broadcaster = broadcaster
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
            if event.data.status != self.handled_status:
                return
            await self.enqueue(application_id=event.data.application_id)
        except Exception as e:
            self._log.warning(
                "Failed to handle ApplicationWSEvent",
                error=str(e),
            )

    async def run(self) -> None:
        if not self._once:
            self._once = True
        else:
            raise RuntimeError("run() can be called once")
        self._log.info("Consumer started")
        try:
            while True:
                application_id = await self.get_next()
                try:
                    await self._process_one(application_id=application_id)
                except Exception as e:
                    self._log.exception(
                        "Consumer iteration failed",
                        application_id=application_id,
                        error=str(e),
                    )
        except asyncio.CancelledError:
            self._log.info("Consumer cancelled")
            raise

    async def _process_one(self, application_id: int) -> None:
        async with self._session_maker() as session:
            app = await ApplicationRepository.get_by_id(
                session=session, application_id=application_id
            )
            if app is None:
                self._log.warning("Application missing", application_id=application_id)
                return
            if app.status != ProcessingState.LETTER_PENDING:
                self._log.warning(
                    "Skipping application not in LETTER_PENDING",
                    application_id=application_id,
                    status=app.status,
                )
                return
            vacancy_id = app.vacancy_id

        try:
            await self._cover_letter_service.regenerate(vacancy_id=vacancy_id)
        except Exception as e:
            self._log.error(
                "LLM generation failed for application",
                application_id=application_id,
                error=str(e),
            )
            async with self._session_maker() as session:
                await self._state_service.transition_or_skip(
                    session=session,
                    application_id=application_id,
                    event=ApplicationEvent.FAIL,
                    error_message=str(e),
                )
