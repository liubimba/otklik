from fastapi import APIRouter, BackgroundTasks
from headhunter_backend.api.dependencies import BrowserDep, BroadcasterDep
from headhunter_backend.api.events import AuthEvent
from headhunter_backend.api.schemas import AuthStatus
from headhunter_backend.log import get_logger

auth_router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger("auth_router")


@auth_router.get("/status")
async def status(browser: BrowserDep) -> AuthStatus:
    logger.info("Requested for status of authentication")
    return await browser.get_auth_status()


@auth_router.post("")
async def auth(
    browser: BrowserDep, broadcaster: BroadcasterDep, background_tasks: BackgroundTasks
) -> AuthStatus:
    logger.info("Requested for authentication")
    auth_status: AuthStatus = await browser.get_auth_status()
    if auth_status.is_authorized():
        return AuthStatus.authorized()
    background_tasks.add_task(_wait_and_announce, browser, broadcaster)
    return AuthStatus.authorizing()


async def _wait_and_announce(browser: BrowserDep, broadcaster: BroadcasterDep) -> None:
    logger.info("Waiting for user to authenticate...")
    await browser.wait_for_login()
    logger.info("User authenticated, broadcasting event...")
    await broadcaster.publish(AuthEvent(data=await browser.get_auth_status()))
