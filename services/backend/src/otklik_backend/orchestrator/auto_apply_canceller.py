from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.log import get_logger
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService
from otklik_backend.orchestrator.workers.letter_pending import LetterPendingWorker
from otklik_backend.orchestrator.workers.letter_sending import LetterSendingWorker


class AutoApplyCanceller:
    def __init__(
        self,
        letter_pending_worker: LetterPendingWorker,
        letter_sending_worker: LetterSendingWorker,
        state_service: StateTransitionService,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        self._letter_pending_worker = letter_pending_worker
        self._letter_sending_worker = letter_sending_worker
        self._state_service = state_service
        self._session_maker = session_maker
        self._log = get_logger(__name__)

    async def cancel_pending(self) -> int:
        dropped = (
            self._letter_pending_worker.clear() + self._letter_sending_worker.clear()
        )
        if not dropped:
            return 0
        async with self._session_maker() as session:
            for application_id in dropped:
                await self._state_service.transition_or_skip(
                    session=session,
                    application_id=application_id,
                    event=ApplicationEvent.CANCEL,
                )
        self._log.info("Cancelled pending auto-apply applications", count=len(dropped))
        return len(dropped)
