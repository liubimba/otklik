# Re-export shim: canonical location for the exception hierarchy is
# core/exceptions.py. ServerError kept as an alias so pre-refactor call
# sites (routes, services) continue to work; the app-level exception
# handler in api/errors.py is registered against DomainError, which
# ServerError is now a subclass of.
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
