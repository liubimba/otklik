import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.selectors import Selectors
from headhunter_backend.browser.writer import (
    BrowserWriter,
    SubmitResult,
    SubmitResultType,
)
from headhunter_backend.core.events import CaptchaData, CaptchaWSEvent
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
        browser: BrowserCore,
        writer: BrowserWriter,
        broadcaster: EventBroadcaster,
        selectors: Selectors,
        rate_limit_backoff_sec: float = 60,
    ) -> None:
        super().__init__()
        self._state_service = state_service
        self._session_maker = session_maker
        self._browser = browser
        self._writer = writer
        self._broadcaster = broadcaster
        self._selectors = selectors
        self._rate_limit_backoff_sec = rate_limit_backoff_sec
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self._pause_reason: str | None = None

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

            match await auth_gate(browser=self._browser):
                case GateResult.NOT_AUTHORIZED:
                    self._log.warning(
                        "Not authorized -- fail. Pause until authorized, use resume() to resume worker",
                        application_id=app.id,
                    )
                    self.pause(reason="not authorized")
                    await self.enqueue(application_id=app.id)
                    await self._fail(
                        application_id=app.id,
                        session=session,
                        reason="not authorized",
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
            if vacancy.response_link is None:
                self._log.warning("Missing response link", application_id=app.id)
                await self._fail(
                    application_id=app.id,
                    session=session,
                    reason="missing response link",
                )
                return

            result: SubmitResult = await self._writer.submit(
                vacancy_url=vacancy.response_link,
                letter_text=letter.text,
                selectors=self._selectors,
            )
            match result.type:
                case SubmitResultType.SUBMITTED:
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
                case SubmitResultType.CAPTCHA:
                    await self.enqueue(application_id=app.id)
                    self.pause(reason="captcha")
                    await self._broadcaster.publish(
                        event=CaptchaWSEvent(
                            data=CaptchaData(
                                vacancy_id=app.vacancy_id, application_id=app.id
                            )
                        )
                    )
                case SubmitResultType.FAILED:
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
