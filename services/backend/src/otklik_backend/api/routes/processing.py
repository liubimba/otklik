from fastapi import APIRouter

from otklik_backend.api.dependencies import (
    AutoApplyCancellerDep,
    PauseControllerDep,
    SessionDep,
)
from otklik_backend.api.schemas import ProcessingStatusAPISchema
from otklik_backend.core.state import ProcessingState
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.settings import SettingsRepository

processing_router: APIRouter = APIRouter(prefix="/processing", tags=["processing"])


async def _in_flight(session: SessionDep) -> int:
    settings = await SettingsRepository.get(session=session)
    states = [ProcessingState.LETTER_QUEUED, ProcessingState.LETTER_SENDING]
    if settings.auto_generate:
        states.append(ProcessingState.LETTER_PENDING)
    if settings.auto_submit:
        states.append(ProcessingState.LETTER_READY)
    return await ApplicationRepository.count_in_states(session=session, states=states)


@processing_router.get("/status")
async def processing_status(
    session: SessionDep, pause_controller: PauseControllerDep
) -> ProcessingStatusAPISchema:
    return ProcessingStatusAPISchema(
        paused=pause_controller.is_paused(),
        in_flight=await _in_flight(session),
    )


@processing_router.post("/pause")
async def processing_pause(pause_controller: PauseControllerDep) -> None:
    pause_controller.pause()


@processing_router.post("/resume")
async def processing_resume(pause_controller: PauseControllerDep) -> None:
    pause_controller.resume()


@processing_router.post("/cancel")
async def processing_cancel(
    session: SessionDep,
    canceller: AutoApplyCancellerDep,
    pause_controller: PauseControllerDep,
) -> ProcessingStatusAPISchema:
    await canceller.cancel_pending()
    pause_controller.resume()
    return ProcessingStatusAPISchema(
        paused=pause_controller.is_paused(),
        in_flight=await _in_flight(session),
    )
