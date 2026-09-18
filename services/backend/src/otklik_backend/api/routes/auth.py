from fastapi import APIRouter

from otklik_backend.api.dependencies import AuthorizationServiceDep
from otklik_backend.api.schemas import AuthStatusAPISchema
from otklik_backend.core.board import DEFAULT_BOARD, Board

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get("/status")
async def status(
    authorization_service: AuthorizationServiceDep,
    board: Board = DEFAULT_BOARD,
) -> AuthStatusAPISchema:
    return await authorization_service.status(board=board)


@auth_router.post("/sign-in")
async def sign_in(
    authorization_service: AuthorizationServiceDep,
    board: Board = DEFAULT_BOARD,
) -> AuthStatusAPISchema:
    return await authorization_service.authorize(board=board)


@auth_router.post("/sign-in/cancel")
async def sign_in_cancel(
    authorization_service: AuthorizationServiceDep,
    board: Board = DEFAULT_BOARD,
) -> AuthStatusAPISchema:
    return await authorization_service.cancel(board=board)


@auth_router.post("/sign-out")
async def sign_out(
    authorization_service: AuthorizationServiceDep,
    board: Board = DEFAULT_BOARD,
) -> AuthStatusAPISchema:
    return await authorization_service.unauthorize(board=board)
