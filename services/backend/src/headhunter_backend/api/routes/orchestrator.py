from fastapi import APIRouter
from headhunter_backend.api.dependencies import OrchestratorDep
from headhunter_backend.api.schemas import OrchestratorStatusAPISchema

orchestrator_router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@orchestrator_router.post(path="/resume")
def resume(orchestrator: OrchestratorDep) -> None:
    orchestrator.resume()


@orchestrator_router.get(path="/status")
def status(orchestrator: OrchestratorDep) -> OrchestratorStatusAPISchema:
    return OrchestratorStatusAPISchema(
        reason=orchestrator.get_pause_reason(),
        paused=orchestrator.is_paused(),
        queue_size=orchestrator.qsize(),
        queue=orchestrator.get_application_ids(),
    )
