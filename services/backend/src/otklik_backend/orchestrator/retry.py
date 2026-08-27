from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.api.schemas import ProcessingState
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService


async def retry_errored_applications(
    session: AsyncSession, state_service: StateTransitionService
) -> int:
    settings = await SettingsRepository.get(session=session)
    if not settings.auto_generate:
        return 0
    errored = await ApplicationRepository.list_by_status(
        session=session, status=ProcessingState.ERROR
    )
    for application in errored:
        await state_service.transition_or_skip(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.RETRY,
        )
    return len(errored)
