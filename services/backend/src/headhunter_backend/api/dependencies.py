from typing import Annotated
from fastapi import Depends
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.browser.core import BrowserCore
from starlette.requests import HTTPConnection


def get_browser(request: HTTPConnection) -> BrowserCore:
    return request.app.state.browser  # type: ignore[no-any-return]


def get_broadcaster(request: HTTPConnection) -> EventBroadcaster:
    return request.app.state.broadcaster  # type: ignore[no-any-return]


BrowserDep = Annotated[BrowserCore, Depends(get_browser)]
BroadcasterDep = Annotated[EventBroadcaster, Depends(get_broadcaster)]
