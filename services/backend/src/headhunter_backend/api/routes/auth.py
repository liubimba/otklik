from fastapi import APIRouter, BackgroundTasks
from headhunter_backend.api.dependencies import BrowserDep, BroadcasterDep
from headhunter_backend.api.events import AuthWSEvent
from headhunter_backend.api.schemas import AuthStatusAPISchema
from headhunter_backend.log import get_logger

auth_router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger("auth_router")


@auth_router.get("/status")
async def status(browser: BrowserDep) -> AuthStatusAPISchema:
    logger.info("Requested for status of authentication")
    return await browser.get_auth_status()


@auth_router.post("")
async def auth(
    browser: BrowserDep, broadcaster: BroadcasterDep, background_tasks: BackgroundTasks
) -> AuthStatusAPISchema:
    logger.info("Requested for authentication")
    auth_status: AuthStatusAPISchema = await browser.get_auth_status()
    if auth_status.is_authorized():
        return AuthStatusAPISchema.authorized()
    background_tasks.add_task(_wait_and_announce, browser, broadcaster)
    return AuthStatusAPISchema.authorizing()


async def _wait_and_announce(browser: BrowserDep, broadcaster: BroadcasterDep) -> None:
    logger.info("Waiting for user to authenticate...")
    await browser.wait_for_login()
    logger.info("User authenticated, broadcasting event...")
    await broadcaster.publish(AuthWSEvent(data=await browser.get_auth_status()))
