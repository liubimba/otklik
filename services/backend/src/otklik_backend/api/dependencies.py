from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from otklik_backend.ai.layer import AILayer
from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.browser.core import BrowserCore
from otklik_backend.db.session import get_session
from otklik_backend.orchestrator.authorization_service import AuthorizationService
from otklik_backend.orchestrator.cover_letter_service import CoverLetterService
from otklik_backend.orchestrator.letter_chat_service import LetterChatService
from otklik_backend.orchestrator.search import SearchService
from otklik_backend.orchestrator.state_service import StateTransitionService
from otklik_backend.orchestrator.workers.letter_sending import LetterSendingWorker
from otklik_backend.setup.benchmark import BenchmarkRunner
from otklik_backend.setup.hardware import HardwareProbe
from otklik_backend.setup.ollama import OllamaGate
from otklik_backend.sites.hh_ru.auth_flow import HHRUAuthFlow
from otklik_backend.sites.hh_ru.writer import HHRUWriter


def get_browser(request: HTTPConnection) -> BrowserCore:
    return request.app.state.browser  # type: ignore[no-any-return]


def get_auth_flow(request: HTTPConnection) -> HHRUAuthFlow:
    return request.app.state.auth_flow  # type: ignore[no-any-return]


def get_broadcaster(request: HTTPConnection) -> EventBroadcaster:
    return request.app.state.broadcaster  # type: ignore[no-any-return]


def get_orchestrator(request: HTTPConnection) -> LetterSendingWorker:
    # AppContext exposes it as letter_sending_worker; alias name kept for
    # the /system/orchestrator/* routes that expose queue/pause status.
    return request.app.state.letter_sending_worker  # type: ignore[no-any-return]


def get_writer(request: HTTPConnection) -> HHRUWriter:
    return request.app.state.writer  # type: ignore[no-any-return]


def get_search_service(request: HTTPConnection) -> SearchService:
    return request.app.state.search_service  # type: ignore[no-any-return]


def get_ai_layer(request: HTTPConnection) -> AILayer:
    return request.app.state.ai_layer  # type: ignore[no-any-return]


def get_cover_letter_service(request: HTTPConnection) -> CoverLetterService:
    return request.app.state.cover_letter_service  # type: ignore[no-any-return]


def get_letter_chat_service(request: HTTPConnection) -> LetterChatService:
    return request.app.state.letter_chat_service  # type: ignore[no-any-return]


def get_authorization_service(request: HTTPConnection) -> AuthorizationService:
    return request.app.state.authorization_service  # type: ignore[no-any-return]


def get_state_service(request: HTTPConnection) -> StateTransitionService:
    return request.app.state.state_service  # type: ignore[no-any-return]


# Три компонента без состояния и без внешних ручек — строим на месте, а не
# тащим через BackendBuilder/app.state: класть в контекст приложения нечего.
def get_hardware_probe() -> HardwareProbe:
    return HardwareProbe()


def get_ollama_gate() -> OllamaGate:
    return OllamaGate()


def get_benchmark_runner() -> BenchmarkRunner:
    return BenchmarkRunner()


BrowserDep = Annotated[BrowserCore, Depends(get_browser)]
AuthFlowDep = Annotated[HHRUAuthFlow, Depends(get_auth_flow)]
BroadcasterDep = Annotated[EventBroadcaster, Depends(get_broadcaster)]
OrchestratorDep = Annotated[LetterSendingWorker, Depends(get_orchestrator)]
WriterDep = Annotated[HHRUWriter, Depends(get_writer)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
AILayerDep = Annotated[AILayer, Depends(get_ai_layer)]
CoverLetterServiceDep = Annotated[CoverLetterService, Depends(get_cover_letter_service)]
LetterChatServiceDep = Annotated[LetterChatService, Depends(get_letter_chat_service)]
AuthorizationServiceDep = Annotated[
    AuthorizationService, Depends(get_authorization_service)
]
StateServiceDep = Annotated[StateTransitionService, Depends(get_state_service)]
HardwareProbeDep = Annotated[HardwareProbe, Depends(get_hardware_probe)]
OllamaGateDep = Annotated[OllamaGate, Depends(get_ollama_gate)]
BenchmarkRunnerDep = Annotated[BenchmarkRunner, Depends(get_benchmark_runner)]
