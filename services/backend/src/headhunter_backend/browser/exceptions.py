from headhunter_backend.exceptions import ServerError


class OpenPageTimeoutError(ServerError):
    status_code = 504
    detail = "Open page timed out"


class ClosePageTimeoutError(ServerError):
    status_code = 504
    detail = "Close page timed out"
