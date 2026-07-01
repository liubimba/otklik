from typing import Annotated
from fastapi import Depends
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.writer import BrowserWriter
from headhunter_backend.orchestrator.authorization_service import AuthorizationService
from headhunter_backend.orchestrator.cover_letter_service import CoverLetterService
from headhunter_backend.orchestrator.queue import Orchestrator
from headhunter_backend.orchestrator.state_service import StateTransitionService
from starlette.requests import HTTPConnection
from sqlalchemy.ext.asyncio import AsyncSession
from headhunter_backend.orchestrator.search import SearchService
from headhunter_backend.db.session import get_session
from headhunter_backend.ai.layer import AILayer


def get_browser(request: HTTPConnection) -> BrowserCore:
    return request.app.state.browser  # type: ignore[no-any-return]


def get_broadcaster(request: HTTPConnection) -> EventBroadcaster:
    return request.app.state.broadcaster  # type: ignore[no-any-return]


def get_orchestrator(request: HTTPConnection) -> Orchestrator:
    return request.app.state.orchestrator  # type: ignore[no-any-return]


def get_writer(request: HTTPConnection) -> BrowserWriter:
    return request.app.state.writer  # type: ignore[no-any-return]


def get_search_service(request: HTTPConnection) -> SearchService:
    return request.app.state.search_service  # type: ignore[no-any-return]


def get_ai_layer(request: HTTPConnection) -> AILayer:
    return request.app.state.ai_layer  # type: ignore[no-any-return]


def get_cover_letter_service(request: HTTPConnection) -> CoverLetterService:
    return request.app.state.cover_letter_service  # type: ignore[no-any-return]


def get_authorization_service(request: HTTPConnection) -> AuthorizationService:
    return request.app.state.authorization_service  # type: ignore[no-any-return]


def get_state_service(request: HTTPConnection) -> StateTransitionService:
    return request.app.state.state_service  # type: ignore[no-any-return]


BrowserDep = Annotated[BrowserCore, Depends(get_browser)]
BroadcasterDep = Annotated[EventBroadcaster, Depends(get_broadcaster)]
OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]
WriterDep = Annotated[BrowserWriter, Depends(get_writer)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
AILayerDep = Annotated[AILayer, Depends(get_ai_layer)]
CoverLetterServiceDep = Annotated[CoverLetterService, Depends(get_cover_letter_service)]
AuthorizationServiceDep = Annotated[
    AuthorizationService, Depends(get_authorization_service)
]
StateServiceDep = Annotated[StateTransitionService, Depends(get_state_service)]
