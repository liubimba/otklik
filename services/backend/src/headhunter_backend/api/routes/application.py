import json
from typing import AsyncIterator, Sequence

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from statemachine.exceptions import TransitionNotAllowed

from headhunter_backend.api.dependencies import (
    LetterChatServiceDep,
    OrchestratorDep,
    SessionDep,
    StateServiceDep,
)
from headhunter_backend.api.schemas import (
    ApplicationDetailAPISchema,
    ChatMessageAPISchema,
    CoverLetterAPISchema,
    CoverLetterRequestAPISchema,
    LetterChatRequestAPISchema,
    ProcessingState,
    SubmitApplicationRequestAPISchema,
)
from headhunter_backend.core.exceptions import DomainError
from headhunter_backend.db.models import ApplicationORM, CoverLetterORM, VacancyORM
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.chat_messages import ChatMessageRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.db.repositories.vacancies import VacancyRepository
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator.state_machine import ApplicationEvent

application_router = APIRouter(
    prefix="/vacancies/{vacancy_id}/application", tags=["application"]
)
log = get_logger(__name__)


async def _load_or_404(session: AsyncSession, vacancy_id: int) -> VacancyORM:
    vacancy = await VacancyRepository.get_by_id(session=session, vacancy_id=vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


async def _build_detail(
    session: AsyncSession, application: ApplicationORM
) -> ApplicationDetailAPISchema:
    letters: Sequence[
        CoverLetterORM
    ] = await CoverLetterRepository.list_by_application_id(
        session=session, application_id=application.id
    )
    latest = max(letters, key=lambda letter: letter.version, default=None)
    return ApplicationDetailAPISchema(
        vacancy_id=application.vacancy_id,
        application_id=application.id,
        retry_count=application.retry_count,
        status=application.status,
        reason=application.error_message,
        created_at=application.created_at,
        updated_at=application.updated_at,
        latest_letter=CoverLetterAPISchema(
            text=latest.text, version=latest.version, created_at=latest.created_at
        )
        if latest is not None
        else None,
        letters_count=len(letters),
    )


@application_router.get("")
async def get_application(
    vacancy_id: int, session: SessionDep
) -> ApplicationDetailAPISchema:
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return await _build_detail(session=session, application=application)


@application_router.get("/letters")
async def get_letters(
    vacancy_id: int, session: SessionDep
) -> Sequence[CoverLetterAPISchema]:
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    letters = await CoverLetterRepository.list_by_application_id(
        session=session, application_id=application.id
    )
    return [
        CoverLetterAPISchema(
            text=letter.text, version=letter.version, created_at=letter.created_at
        )
        for letter in letters
    ]


@application_router.post("/generate")
async def generate(
    vacancy_id: int,
    session: SessionDep,
    state_service: StateServiceDep,
) -> ApplicationDetailAPISchema:
    """Kick off async letter generation.

    Auto-creates the Application if needed, then fires the REGENERATE
    event so the state machine lands in LETTER_PENDING. That transition
    publishes an ApplicationWSEvent which LetterPendingWorker picks up
    to run the LLM — the handler does NOT wait for the LLM. Returns the
    ApplicationDetail with status=LETTER_PENDING, so the UI can render a
    durable spinner keyed on the state machine (backend is the source
    of truth, frontend just displays it) until letter_ready arrives.

    Prior implementation blocked here for the full LLM span and returned
    status=LETTER_READY directly; the transient LETTER_PENDING was too
    short-lived to catch a WS refetch, so the spinner never appeared
    (regression reported 2026-07-02).
    """
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        application = await ApplicationRepository.create(
            session=session, vacancy_id=vacancy_id
        )
    if application.status == ProcessingState.LETTER_PENDING:
        # Idempotent: an earlier /generate is already being processed by
        # LetterPendingWorker. Return current state without firing the
        # transition again (would be a no-op arc anyway, but avoids a
        # duplicate WS event that would re-enqueue the same application).
        return await _build_detail(session=session, application=application)
    try:
        application = await state_service.transition(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.REGENERATE,
        )
    except TransitionNotAllowed as e:
        # Terminal/in-flight states have no arc into LETTER_PENDING:
        # LETTER_SENDING, LETTER_SENT, SKIPPED. 409 with the cause so
        # the UI surfaces it via toast instead of hanging.
        raise HTTPException(status_code=409, detail=f"Cannot regenerate letter: {e}")
    return await _build_detail(session=session, application=application)


@application_router.post("/save")
async def save(
    vacancy_id: int,
    letter: CoverLetterRequestAPISchema,
    session: SessionDep,
) -> CoverLetterAPISchema:
    """Save a draft version of the letter. Pure content write — does NOT drive
    the state machine (unlike the removed POST /cover_letter which secretly
    transitioned LETTER_PENDING → LETTER_GENERATED)."""
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(
            status_code=409, detail="Application does not exist for this vacancy"
        )
    created = await CoverLetterRepository.create(
        session=session,
        application_id=application.id,
        text=letter.text,
        source="manual",
    )
    return CoverLetterAPISchema(
        text=created.text, version=created.version, created_at=created.created_at
    )


@application_router.post("/submit", status_code=status.HTTP_200_OK)
async def submit(
    vacancy_id: int,
    body: SubmitApplicationRequestAPISchema,
    session: SessionDep,
    state_service: StateServiceDep,
    orchestrator: OrchestratorDep,
) -> ApplicationDetailAPISchema:
    """Submit the application to hh.ru. If `text` is provided, saves it as a
    new letter version first (atomic dirty-submit)."""
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(
            status_code=409, detail="Application does not exist for this vacancy"
        )
    # Refuse SUBMIT when the letter-sending worker is paused: the state
    # machine would happily accept ERROR → LETTER_SENDING (or the two
    # other SUBMIT arcs), but the worker is blocked on `_resume_event`,
    # so the application would just sit in LETTER_SENDING with no
    # progress until the pause is lifted (which for NOT_AUTHORIZED
    # requires an AuthWSEvent(authorized) — precisely the condition the
    # user cannot satisfy while their session is broken). Surface the
    # pause reason so the UI can prompt for re-auth / captcha resolution
    # instead of showing an infinite spinner.
    if orchestrator.is_paused():
        reason = orchestrator.get_pause_reason() or "unknown"
        raise HTTPException(
            status_code=409,
            detail=f"Cannot submit application: worker is paused ({reason})",
        )
    if body.text is not None:
        await CoverLetterRepository.create(
            session=session,
            application_id=application.id,
            text=body.text,
            source="manual",
        )
    try:
        application = await state_service.transition(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.SUBMIT,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot submit application: {e}",
        )
    return await _build_detail(session=session, application=application)


@application_router.post("/skip")
async def skip(
    vacancy_id: int, session: SessionDep, state_service: StateServiceDep
) -> ApplicationDetailAPISchema:
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=409, detail="Application does not exist")
    try:
        application = await state_service.transition(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.SKIP,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(status_code=409, detail=f"Cannot skip: {e}")
    return await _build_detail(session=session, application=application)


@application_router.post("/retry")
async def retry(
    vacancy_id: int, session: SessionDep, state_service: StateServiceDep
) -> ApplicationDetailAPISchema:
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        raise HTTPException(status_code=409, detail="Application does not exist")
    try:
        application = await state_service.transition(
            session=session,
            application_id=application.id,
            event=ApplicationEvent.RETRY,
        )
    except TransitionNotAllowed as e:
        raise HTTPException(status_code=409, detail=f"Cannot retry: {e}")
    return await _build_detail(session=session, application=application)


@application_router.get("/chat")
async def chat_history(
    vacancy_id: int, session: SessionDep
) -> Sequence[ChatMessageAPISchema]:
    """The persisted letter-editing conversation for this application."""
    await _load_or_404(session, vacancy_id)
    application = await ApplicationRepository.get_by_vacancy_id(
        session=session, vacancy_id=vacancy_id
    )
    if application is None:
        return []
    messages = await ChatMessageRepository.list_by_application_id(
        session=session, application_id=application.id
    )
    return [
        ChatMessageAPISchema(
            id=m.id,
            role=m.role,
            content=m.content,
            produced_version=m.produced_version,
            created_at=m.created_at,
        )
        for m in messages
    ]


@application_router.post("/chat")
async def chat(
    vacancy_id: int,
    body: LetterChatRequestAPISchema,
    chat_service: LetterChatServiceDep,
) -> StreamingResponse:
    """Stream one letter-editing turn as SSE.

    Emits `reply`/`letter` delta events, then a `done` event carrying the new
    letter version (or null for a pure answer). Because the response has
    already committed 200 once streaming starts, domain errors (not editable,
    AI unhealthy, …) are delivered in-band as an `error` event rather than an
    HTTP status.
    """

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in chat_service.stream_turn(vacancy_id, body.message):
                yield f"data: {json.dumps(event)}\n\n"
        except DomainError as exc:
            log.warning("Letter chat rejected", detail=exc.detail)
            yield f"data: {json.dumps({'type': 'error', 'detail': exc.detail})}\n\n"
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            log.error("Letter chat failed", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Chat failed'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
