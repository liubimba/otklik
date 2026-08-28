from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.api.schemas import ProcessingState
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService

IN_FLIGHT_STATES = (
    ProcessingState.LETTER_PENDING,
    ProcessingState.LETTER_QUEUED,
    ProcessingState.LETTER_SENDING,
)


async def park_in_flight_applications(
    session: AsyncSession, state_service: StateTransitionService
) -> int:
    parked = 0
    for status in IN_FLIGHT_STATES:
        applications = await ApplicationRepository.list_by_status(
            session=session, status=status
        )
        for application in applications:
            await state_service.transition_or_skip(
                session=session,
                application_id=application.id,
                event=ApplicationEvent.INTERRUPT,
            )
            parked += 1
    return parked


class InFlightRecovery:
    def __init__(self, state_service: StateTransitionService) -> None:
        self._state_service = state_service

    async def recover(self, session: AsyncSession) -> int:
        return await park_in_flight_applications(
            session=session, state_service=self._state_service
        )
