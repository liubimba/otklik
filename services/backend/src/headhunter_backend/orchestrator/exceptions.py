from headhunter_backend.exceptions import ServerError


class FilterSessionNotFoundError(ServerError):
    status_code = 404
    detail = "Filter session not found"


class FilterSessionClosedError(ServerError):
    status_code = 409
    detail = "Filter session is closed"


class SearchAlreadyRunningError(ServerError):
    status_code = 409
    detail = "Search service busy right now by another search task"


class InvalidSearchURLError(ServerError):
    status_code = 422
    detail = "Search URL must be on hh.ru"
