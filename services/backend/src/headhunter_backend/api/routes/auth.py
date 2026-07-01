from fastapi import APIRouter

from headhunter_backend.api.dependencies import AuthorizationServiceDep
from headhunter_backend.api.schemas import AuthStatusAPISchema

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get("/status")
async def status(authorization_service: AuthorizationServiceDep) -> AuthStatusAPISchema:
    return await authorization_service.status()


@auth_router.post("/sign-in")
async def sign_in(
    authorization_service: AuthorizationServiceDep,
) -> AuthStatusAPISchema:
    return await authorization_service.authorize()


@auth_router.post("/sign-in/cancel")
async def sign_in_cancel(
    authorization_service: AuthorizationServiceDep,
) -> AuthStatusAPISchema:
    return await authorization_service.cancel()


@auth_router.post("/sign-out")
async def sign_out(
    authorization_service: AuthorizationServiceDep,
) -> AuthStatusAPISchema:
    return await authorization_service.unauthorize()
