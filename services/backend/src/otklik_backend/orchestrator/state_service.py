from sqlalchemy.ext.asyncio import AsyncSession
from statemachine.exceptions import TransitionNotAllowed

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.core.events import ApplicationData, ApplicationWSEvent
from otklik_backend.db.models import ApplicationORM
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.exceptions import ApplicationNotFoundError
from otklik_backend.log import get_logger
from otklik_backend.orchestrator.state_machine import ApplicationEvent


class StateTransitionService:
    def __init__(self, broadcaster: EventBroadcaster) -> None:
        self._broadcaster = broadcaster
        self._log = get_logger(__name__)

    async def transition(
        self,
        session: AsyncSession,
        application_id: int,
        event: ApplicationEvent,
        error_message: str | None = None,
        reason: str | None = None,
    ) -> ApplicationORM:
        application = await ApplicationRepository.transition(
            session=session,
            application_id=application_id,
            to_state=event,
            error_message=error_message,
        )
        if application is None:
            raise ApplicationNotFoundError()
        await self._broadcaster.publish(
            event=ApplicationWSEvent(
                data=ApplicationData(
                    vacancy_id=application.vacancy_id,
                    application_id=application.id,
                    status=application.status,
                    reason=(
                        reason if reason is not None else application.error_message
                    ),
                    error_domain=application.error_domain,
                )
            )
        )
        return application

    async def transition_or_skip(
        self,
        session: AsyncSession,
        application_id: int,
        event: ApplicationEvent,
        error_message: str | None = None,
        reason: str | None = None,
    ) -> ApplicationORM | None:
        try:
            return await self.transition(
                session=session,
                application_id=application_id,
                event=event,
                error_message=error_message,
                reason=reason,
            )
        except TransitionNotAllowed:
            self._log.warning(
                "Transition not allowed — skipping",
                application_id=application_id,
                event=event.value,
            )
            return None
        except ApplicationNotFoundError:
            self._log.warning(
                "Application missing — skipping transition",
                application_id=application_id,
                event=event.value,
            )
            return None
