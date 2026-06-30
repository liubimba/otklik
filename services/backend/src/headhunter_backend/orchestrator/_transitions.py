from sqlalchemy.ext.asyncio import AsyncSession

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.events import ApplicationData, ApplicationWSEvent
from headhunter_backend.db.crud import transition_application
from headhunter_backend.db.models import ApplicationORM
from headhunter_backend.exceptions import ApplicationNotFoundError
from headhunter_backend.orchestrator.state_machine import ApplicationEvent


# Removed in stage 3.2 — replaced by StateTransitionService.
async def transition_and_broadcast(
    *,
    session: AsyncSession,
    broadcaster: EventBroadcaster,
    application_id: int,
    to_state: ApplicationEvent,
    error_message: str | None = None,
    reason: str | None = None,
) -> ApplicationORM:
    application: ApplicationORM | None = await transition_application(
        session=session,
        application_id=application_id,
        to_state=to_state,
        error_message=error_message,
    )
    if application is None:
        raise ApplicationNotFoundError()
    await broadcaster.publish(
        event=ApplicationWSEvent(
            data=ApplicationData(
                vacancy_id=application.vacancy_id,
                application_id=application.id,
                status=application.status,
                reason=reason if reason is not None else application.error_message,
            )
        )
    )
    return application
