import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import Sequence

from headhunter_backend.log import get_logger
from headhunter_backend.db.crud import (
    list_active_applications,
    get_application_by_id,
    get_latest_cover_letter,
    get_vacancy,
    log_submission,
)
from headhunter_backend.db.models import ApplicationORM, CoverLetterORM, VacancyORM
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.writer import (
    BrowserWriter,
    SubmitResultType,
    SubmitResult,
)
from headhunter_backend.browser.selectors import Selectors
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.events import (
    CaptchaWSEvent,
    CaptchaData,
)
from headhunter_backend.orchestrator._transitions import transition_and_broadcast
from headhunter_backend.orchestrator.state_machine import ApplicationEvent
from headhunter_backend.orchestrator.rate_limiter import (
    ensure_within_limits,
    RateLimitExceeded,
)
from headhunter_backend.api.schemas import AuthStatusAPISchema, ProcessingState
from headhunter_backend.exceptions import ApplicationNotFoundError


class Orchestrator:
    def __init__(self) -> None:
        self._log = get_logger(__name__)
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._pending: list[int] = []
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self._once = False
        self._pause_reason: str | None = None

    def pause(self, reason: str | None = None) -> None:
        self._resume_event.clear()
        self._pause_reason = reason
        self._log.info("Orchestrator paused", reason=reason)

    def resume(self) -> None:
        self._resume_event.set()
        self._pause_reason = None
        self._log.info("Orchestrator resumed")

    def is_paused(self) -> bool:
        return not self._resume_event.is_set()

    def get_pause_reason(self) -> str | None:
        return self._pause_reason

    async def enqueue(self, application_id: int) -> None:
        await self._queue.put(application_id)
        self._pending.append(application_id)

    async def get_next(self) -> int:
        application_id = await self._queue.get()
        try:
            self._pending.remove(application_id)
        except ValueError:
            pass
        return application_id

    def qsize(self) -> int:
        return self._queue.qsize()

    def get_application_ids(self) -> Sequence[int]:
        return list(self._pending)

    async def recover_from_db(self, session: AsyncSession) -> int:
        applications: Sequence[ApplicationORM] = await list_active_applications(session)
        for application in applications:
            await self.enqueue(application_id=application.id)
        return len(applications)

    async def consume(
        self,
        writer: BrowserWriter,
        session_maker: async_sessionmaker[AsyncSession],
        browser: BrowserCore,
        broadcaster: EventBroadcaster,
        selectors: Selectors,
        rate_limit_backoff_sec: float = 60,
    ) -> None:
        if not self._once:
            self._once = True
        else:
            raise Exception("consume can be called once")
        self._log.info("Consumer started")
        try:
            while True:
                await self._resume_event.wait()
                application_id: int = await self.get_next()
                try:
                    await self._process_one(
                        application_id=application_id,
                        session_maker=session_maker,
                        browser=browser,
                        broadcaster=broadcaster,
                        writer=writer,
                        selectors=selectors,
                        rate_limit_backoff_sec=rate_limit_backoff_sec,
                    )
                except Exception as e:
                    self._log.exception(
                        "Consumer iteration failed",
                        application_id=application_id,
                        error=str(e),
                    )
        except asyncio.CancelledError:
            self._log.info("Consumer cancelled")
            raise

    async def _process_one(
        self,
        application_id: int,
        session_maker: async_sessionmaker[AsyncSession],
        browser: BrowserCore,
        broadcaster: EventBroadcaster,
        writer: BrowserWriter,
        selectors: Selectors,
        rate_limit_backoff_sec: float,
    ) -> None:
        async with session_maker() as session:
            app: ApplicationORM | None = await get_application_by_id(
                session=session, application_id=application_id
            )
            if app is None:
                self._log.warning("Application missing", application_id=application_id)
                return

            if app.status != ProcessingState.LETTER_SENDING:
                self._log.warning(
                    "Skipping application not in LETTER_SENDING", application_id=app.id
                )
                return

            # 1 Auth
            auth_status: AuthStatusAPISchema = await browser.get_auth_status()
            if not auth_status.is_authorized():
                self._log.warning(
                    "Not authorized -- fail. Pause until authorized, use resume() to resume orchestrator",
                    application_id=app.id,
                    auth_status=auth_status,
                )
                self.pause(reason="not authorized")
                await self.enqueue(application_id=app.id)
                await self._fail(
                    application_id=app.id,
                    session=session,
                    vacancy_id=app.vacancy_id,
                    reason="not authorized",
                    broadcaster=broadcaster,
                )
                return

            # 2 Rate-limit
            try:
                await ensure_within_limits(session=session)
            except RateLimitExceeded:
                self._log.warning("Rate limit hit -- re-enqueue + backoff")
                await self.enqueue(application_id=app.id)
                await asyncio.sleep(delay=rate_limit_backoff_sec)
                return

            # 3 Get cover letter
            letter: CoverLetterORM | None = await get_latest_cover_letter(
                session=session, application_id=app.id
            )
            if letter is None:
                self._log.warning(
                    "Missing cover letter. Pause until restore cover letter, use resume() to resume orchestrator",
                    application_id=app.id,
                )
                self.pause(reason="missing cover letter")
                await self.enqueue(application_id=app.id)
                await self._fail(
                    application_id=app.id,
                    session=session,
                    vacancy_id=app.vacancy_id,
                    reason="missing cover leter",
                    broadcaster=broadcaster,
                )
                return

            vacancy: VacancyORM | None = await get_vacancy(
                session=session, vacancy_id=app.vacancy_id
            )
            if vacancy is None:
                self._log.warning("Missing vacancy", application_id=app.id)
                await self._fail(
                    application_id=app.id,
                    session=session,
                    vacancy_id=app.vacancy_id,
                    reason="missing vacancy",
                    broadcaster=broadcaster,
                )
                return
            if vacancy.response_link is None:
                self._log.warning("Missing response link", application_id=app.id)
                await self._fail(
                    application_id=app.id,
                    session=session,
                    vacancy_id=app.vacancy_id,
                    reason="missing response link",
                    broadcaster=broadcaster,
                )
                return

            # 4 Writer
            result: SubmitResult = await writer.submit(
                vacancy_url=vacancy.response_link,
                letter_text=letter.text,
                selectors=selectors,
            )
            match result.type:
                case SubmitResultType.SUBMITTED:
                    await log_submission(session=session)
                    try:
                        await transition_and_broadcast(
                            session=session,
                            broadcaster=broadcaster,
                            application_id=app.id,
                            to_state=ApplicationEvent.SUBMISSION_OK,
                        )
                    except ApplicationNotFoundError:
                        self._log.error("Failed to transition to SUBMISSION_OK")
                        return
                case SubmitResultType.CAPTCHA:
                    await self.enqueue(application_id=app.id)
                    self.pause(reason="captcha")
                    await broadcaster.publish(
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
                        vacancy_id=app.vacancy_id,
                        reason=result.reason or "unknown",
                        broadcaster=broadcaster,
                    )

    async def _fail(
        self,
        application_id: int,
        session: AsyncSession,
        vacancy_id: int,
        reason: str,
        broadcaster: EventBroadcaster,
    ) -> None:
        try:
            await transition_and_broadcast(
                session=session,
                broadcaster=broadcaster,
                application_id=application_id,
                to_state=ApplicationEvent.SUBMISSION_FAILED,
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
