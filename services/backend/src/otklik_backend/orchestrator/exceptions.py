from otklik_backend.exceptions import ServerError


class FilterSessionNotFoundError(ServerError):
    status_code = 404
    detail = "Filter session not found"


class FilterSessionClosedError(ServerError):
    status_code = 409
    detail = "Filter session is closed"


class SearchAlreadyRunningError(ServerError):
    status_code = 409
    detail = "Search service busy right now by another search task"


class SearchSessionNotFoundError(ServerError):
    status_code = 404
    detail = "Search session not found"


class InvalidSearchURLError(ServerError):
    status_code = 422
    detail = "Search URL must be on hh.ru"


class FilterSessionRunningAlreadyError(ServerError):
    status_code = 422
    detail = "Filter session busy right now by another search task"
    code = "filter_session_running"


class LetterChatNotAllowedError(ServerError):
    status_code = 409
    detail = "Letter cannot be edited via chat in the current state"
    code = "letter_chat_not_allowed"
