from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.core.state import ErrorDomain
from otklik_backend.api.schemas import ProcessingState
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.cover_letters import CoverLetterRepository
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.orchestrator.state_machine import ApplicationEvent
from otklik_backend.orchestrator.state_service import StateTransitionService


async def _has_letter(session: AsyncSession, application_id: int) -> bool:
    latest = await CoverLetterRepository.get_latest_by_application_id(
        session=session, application_id=application_id
    )
    return latest is not None


async def generation_targets(
    session: AsyncSession, search_id: str | None = None
) -> list[int]:
    interrupted = await ApplicationRepository.list_by_status(
        session=session, status=ProcessingState.INTERRUPTED, search_id=search_id
    )
    errored = await ApplicationRepository.list_by_status(
        session=session, status=ProcessingState.ERROR, search_id=search_id
    )
    ids: list[int] = []
    for application in interrupted:
        if not await _has_letter(session=session, application_id=application.id):
            ids.append(application.id)
    for application in errored:
        if application.error_domain == ErrorDomain.MODEL:
            ids.append(application.id)
    return ids


async def submission_targets(
    session: AsyncSession, search_id: str | None = None
) -> list[int]:
    interrupted = await ApplicationRepository.list_by_status(
        session=session, status=ProcessingState.INTERRUPTED, search_id=search_id
    )
    errored = await ApplicationRepository.list_by_status(
        session=session, status=ProcessingState.ERROR, search_id=search_id
    )
    ids: list[int] = []
    for application in interrupted:
        if await _has_letter(session=session, application_id=application.id):
            ids.append(application.id)
    for application in errored:
        if application.error_domain == ErrorDomain.SUBMISSION:
            ids.append(application.id)
    return ids


async def restart_generation(
    session: AsyncSession,
    state_service: StateTransitionService,
    search_id: str | None = None,
) -> int:
    settings = await SettingsRepository.get(session=session)
    if not settings.auto_generate:
        return 0
    ids = await generation_targets(session=session, search_id=search_id)
    for application_id in ids:
        await state_service.transition_or_skip(
            session=session,
            application_id=application_id,
            event=ApplicationEvent.REGENERATE,
        )
    return len(ids)


async def restart_submission(
    session: AsyncSession,
    state_service: StateTransitionService,
    search_id: str | None = None,
) -> int:
    settings = await SettingsRepository.get(session=session)
    if not settings.auto_submit:
        return 0
    ids = await submission_targets(session=session, search_id=search_id)
    for application_id in ids:
        await state_service.transition_or_skip(
            session=session,
            application_id=application_id,
            event=ApplicationEvent.SUBMIT,
        )
    return len(ids)


async def restart_counts(
    session: AsyncSession, search_id: str | None = None
) -> tuple[int, int]:
    generation = len(await generation_targets(session=session, search_id=search_id))
    submission = len(await submission_targets(session=session, search_id=search_id))
    return generation, submission
