class DomainError(Exception):
    status_code: int = 500
    detail: str = "Internal server error"
    code: str = "DOMAIN_ERROR"


class NotFoundError(DomainError):
    status_code = 404
    detail = "Not found"
    code = "NOT_FOUND"


class ConflictError(DomainError):
    status_code = 409
    detail = "Conflict"
    code = "CONFLICT"


class RateLimitedError(DomainError):
    status_code = 429
    detail = "Rate limited"
    code = "RATE_LIMITED"


class ServiceUnavailableError(DomainError):
    status_code = 503
    detail = "Service unavailable"
    code = "SERVICE_UNAVAILABLE"
