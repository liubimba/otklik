from fastapi import APIRouter
from headhunter_backend.api.dependencies import OrchestratorDep

orchestrator_router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@orchestrator_router.post(path="/resume")
def resume(orchestrator: OrchestratorDep) -> None:
    orchestrator.resume()
