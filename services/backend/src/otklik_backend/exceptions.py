from otklik_backend.core.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    RateLimitedError,
    ServiceUnavailableError,
)


ServerError = DomainError


class VacancyNotFoundError(NotFoundError):
    detail = "Vacancy not found"
    code = "VACANCY_NOT_FOUND"


class ApplicationNotFoundError(ConflictError):
    detail = "Application not found"
    code = "APPLICATION_NOT_FOUND"


__all__ = [
    "ApplicationNotFoundError",
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "RateLimitedError",
    "ServerError",
    "ServiceUnavailableError",
    "VacancyNotFoundError",
]
