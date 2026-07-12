from otklik_backend.exceptions import ServerError


class OpenPageTimeoutError(ServerError):
    status_code = 504
    detail = "Open page timed out"


class ClosePageTimeoutError(ServerError):
    status_code = 504
    detail = "Close page timed out"


class BrowserNetworkError(ServerError):
    status_code = 503
    detail = "Browser network error"
    code = "BROWSER_NETWORK_ERROR"
