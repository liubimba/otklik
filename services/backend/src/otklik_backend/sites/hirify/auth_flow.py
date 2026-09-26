from otklik_backend.api.schemas import AuthStatusAPISchema
from otklik_backend.browser.core import BrowserCore
from otklik_backend.log import get_logger


class HirifyAuthFlow:
    def __init__(self, browser: BrowserCore) -> None:
        self._browser = browser
        self._log = get_logger(self.__class__.__name__)

    async def get_auth_status(self) -> AuthStatusAPISchema:
        return AuthStatusAPISchema.authorized()

    async def wait_for_login(self, poll_interval: float = 1.0) -> None:
        return None

    async def unauthorize(self) -> None:
        return None
