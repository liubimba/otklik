# Re-export shim: canonical location is now core/events.py. Kept during
# stage 2/3 migration so existing callers continue to work. Remove in
# stage 3.2/2.6 once every site imports from core.events directly.
from headhunter_backend.core.events import (
    ApplicationData,
    ApplicationWSEvent,
    AuthWSEvent,
    CaptchaData,
    CaptchaWSEvent,
    SearchData,
    SearchWSEvent,
    VacancyWSEvent,
)

__all__ = [
    "ApplicationData",
    "ApplicationWSEvent",
    "AuthWSEvent",
    "CaptchaData",
    "CaptchaWSEvent",
    "SearchData",
    "SearchWSEvent",
    "VacancyWSEvent",
]
