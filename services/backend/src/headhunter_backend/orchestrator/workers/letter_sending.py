import asyncio

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.subscribers import CallbackEventSubscriber
from headhunter_backend.core.events import (
    ApplicationWSEvent,
    AuthWSEvent,
    CaptchaData,
    CaptchaWSEvent,
)
from headhunter_backend.core.site import SiteAuthFlow, SiteWriter
from headhunter_backend.core.site.result import SubmissionResult, SubmissionResultType
from headhunter_backend.core.state import ProcessingState
from headhunter_backend.db.models import ApplicationORM, CoverLetterORM, VacancyORM
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.db.repositories.rate_limits import RateLimitRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.exceptions import ApplicationNotFoundError
from headhunter_backend.orchestrator.gates import GateResult, auth_gate, rate_limit_gate
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.orchestrator.state_service import StateTransitionService
from headhunter_backend.orchestrator.workers.base import Worker


class LetterSendingWorker(Worker):
    handled_status = ProcessingState.LETTER_SENDING

    def __init__(
        self,
        state_service: StateTransitionService,
        session_maker: async_sessionmaker[AsyncSession],
        auth_flow: SiteAuthFlow,
        writer: SiteWriter,
        broadcaster: EventBroadcaster,
        rate_limit_backoff_sec: float = 60,
    ) -> None:
        super().__init__()
        self._state_service = state_service
        self._session_maker = session_maker
        self._auth_flow = auth_flow
        self._writer = writer
        self._broadcaster = broadcaster
        self._rate_limit_backoff_sec = rate_limit_backoff_sec
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self._pause_reason: str | None = None
        self._subscriber: CallbackEventSubscriber | None = None

    def start(self) -> None:
        # Subscribe to ApplicationWSEvent — self-enqueue on LETTER_SENDING.
        # Callback wraps enqueue in try/except so a broadcaster _deliver
        # failure never unregisters the worker.
        subscriber = CallbackEventSubscriber.from_callback(
            lambda event: self._on_event(event=event)
        )
        self._broadcaster.register(subscriber)
        self._subscriber = subscriber

    def stop(self) -> None:
        if self._subscriber is not None:
            self._broadcaster.unregister(self._subscriber)
            self._subscriber = None

    # Marker string for the pause reason set on NOT_AUTHORIZED. Kept as a
    # class-level constant so the AuthWSEvent auto-resume path can compare
    # against exactly the same value without a magic string.
    PAUSE_REASON_NOT_AUTHORIZED: str = "not authorized"

    async def _on_event(self, event: BaseModel) -> None:
        try:
            if isinstance(event, AuthWSEvent):
                self._on_auth_event(event=event)
                return
            if isinstance(event, ApplicationWSEvent):
                if event.data.status != self.handled_status:
                    return
                await self.enqueue(application_id=event.data.application_id)
        except Exception as e:
            self._log.warning(
                "Failed to handle event",
                error=str(e),
            )

    def _on_auth_event(self, event: AuthWSEvent) -> None:
        """Auto-resume when the user re-authenticates.

        The worker pauses itself on `auth_gate → NOT_AUTHORIZED` so a burst
        of pending applications isn't wholesale-failed while the session is
        broken. Without this hook the user would have to hit
        `POST /system/orchestrator/resume` by hand after every re-login,
        even though the fix (an authorized session) is already visible on
        the broadcaster.
        """
        if not self.is_paused():
            return
        if self._pause_reason != self.PAUSE_REASON_NOT_AUTHORIZED:
            # Captcha pauses and any other cause are handled elsewhere —
            # do not steal them.
            return
        if not event.data.is_authorized():
            return
        self._log.info("Auth restored — auto-resuming worker")
        self.resume()

    def pause(self, reason: str | None = None) -> None:
        self._resume_event.clear()
        self._pause_reason = reason
        self._log.info("Worker paused", reason=reason)

    def resume(self) -> None:
        self._resume_event.set()
        self._pause_reason = None
        self._log.info("Worker resumed")

    def is_paused(self) -> bool:
        return not self._resume_event.is_set()

    def get_pause_reason(self) -> str | None:
        return self._pause_reason

    async def run(self) -> None:
        if not self._once:
            self._once = True
        else:
            raise RuntimeError("run() can be called once")
        self._log.info("Consumer started")
        try:
            while True:
                await self._resume_event.wait()
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
            app: ApplicationORM | None = await ApplicationRepository.get_by_id(
                session=session, application_id=application_id
            )
            if app is None:
                self._log.warning("Application missing", application_id=application_id)
                return

            if app.status != ProcessingState.LETTER_SENDING:
                self._log.warning(
                    "Skipping application not in LETTER_SENDING",
                    application_id=app.id,
                )
                return

            match await auth_gate(auth_flow=self._auth_flow):
                case GateResult.NOT_AUTHORIZED:
                    self._log.warning(
                        "Not authorized -- fail. Worker paused; AuthWSEvent(authorized) will resume it automatically",
                        application_id=app.id,
                    )
                    self.pause(reason=self.PAUSE_REASON_NOT_AUTHORIZED)
                    await self.enqueue(application_id=app.id)
                    await self._fail(
                        application_id=app.id,
                        session=session,
                        reason=self.PAUSE_REASON_NOT_AUTHORIZED,
                    )
                    return
                case _:
                    pass

            match await rate_limit_gate(session=session):
                case GateResult.RATE_LIMITED:
                    self._log.warning("Rate limit hit -- re-enqueue + backoff")
                    await self.enqueue(application_id=app.id)
                    await asyncio.sleep(delay=self._rate_limit_backoff_sec)
                    return
                case _:
                    pass

            letter: (
                CoverLetterORM | None
            ) = await CoverLetterRepository.get_latest_by_application_id(
                session=session, application_id=app.id
            )
            if letter is None:
                self._log.warning(
                    "Missing cover letter. Pause until restore cover letter, use resume() to resume worker",
                    application_id=app.id,
                )
                self.pause(reason="missing cover letter")
                await self.enqueue(application_id=app.id)
                await self._fail(
                    application_id=app.id,
                    session=session,
                    reason="missing cover leter",
                )
                return

            vacancy: VacancyORM | None = await VacancyRepository.get_by_id(
                session=session, vacancy_id=app.vacancy_id
            )
            if vacancy is None:
                self._log.warning("Missing vacancy", application_id=app.id)
                await self._fail(
                    application_id=app.id,
                    session=session,
                    reason="missing vacancy",
                )
                return

            # Navigate to Vacancy.apply_link — the canonical detail page
            # where the respond link lives. There is no separate stored
            # URL for the response form: the writer reaches it by
            # clicking through the detail page, matching human flow
            # (better for anti-bot). apply_link is NOT NULL by schema,
            # so no missing-URL guard is needed; a stale vacancy that no
            # longer accepts responses is caught downstream by
            # writer.wait_for_selector on the respond link.
            result: SubmissionResult = await self._writer.submit(
                vacancy_url=vacancy.apply_link,
                letter_text=letter.text,
            )
            match result.type:
                case SubmissionResultType.SUBMITTED:
                    await RateLimitRepository.log_submission(session=session)
                    try:
                        await self._state_service.transition(
                            session=session,
                            application_id=app.id,
                            event=ApplicationEvent.SUBMISSION_OK,
                        )
                    except ApplicationNotFoundError:
                        self._log.error("Failed to transition to SUBMISSION_OK")
                        return
                case SubmissionResultType.CAPTCHA:
                    await self.enqueue(application_id=app.id)
                    self.pause(reason="captcha")
                    await self._broadcaster.publish(
                        event=CaptchaWSEvent(
                            data=CaptchaData(
                                vacancy_id=app.vacancy_id, application_id=app.id
                            )
                        )
                    )
                case SubmissionResultType.FAILED:
                    await self._fail(
                        application_id=app.id,
                        session=session,
                        reason=result.reason or "unknown",
                    )

    async def _fail(
        self,
        application_id: int,
        session: AsyncSession,
        reason: str,
    ) -> None:
        try:
            await self._state_service.transition(
                session=session,
                application_id=application_id,
                event=ApplicationEvent.SUBMISSION_FAILED,
                reason=reason,
            )
        except ApplicationNotFoundError:
            self._log.error(
                "Failed to find application to transition to SUBMISSION_FAILED"
            )
        except Exception as e:
            self._log.exception(
                "Failed to transition to SUBMISSION_FAILED", error=str(e)
            )
