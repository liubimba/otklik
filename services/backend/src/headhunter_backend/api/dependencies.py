from typing import Annotated
from fastapi import Depends
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.orchestrator.queue import Orchestrator
from starlette.requests import HTTPConnection
from sqlalchemy.ext.asyncio import AsyncSession
from headhunter_backend.db.session import get_session


def get_browser(request: HTTPConnection) -> BrowserCore:
    return request.app.state.browser  # type: ignore[no-any-return]


def get_broadcaster(request: HTTPConnection) -> EventBroadcaster:
    return request.app.state.broadcaster  # type: ignore[no-any-return]


def get_orchestrator(request: HTTPConnection) -> Orchestrator:
    return request.app.state.orchestrator  # type: ignore[no-any-return]


BrowserDep = Annotated[BrowserCore, Depends(get_browser)]
BroadcasterDep = Annotated[EventBroadcaster, Depends(get_broadcaster)]
OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
