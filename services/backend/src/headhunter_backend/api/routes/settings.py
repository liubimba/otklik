from fastapi import APIRouter
from headhunter_backend.api.schemas import RateLimits, Settings

settings_router: APIRouter = APIRouter(prefix="/settings", tags=["settings"])
_settings: Settings = Settings(
    letter_style="formal",
    resume_text="Experienced software engineer with a strong background in Python and FastAPI.",
    rate_limits=RateLimits(),
)


@settings_router.get("/")
def get_settings() -> Settings:
    return _settings


@settings_router.put("/")
def update_settings(new_settings: Settings) -> Settings:
    global _settings
    _settings = new_settings
    return _settings
