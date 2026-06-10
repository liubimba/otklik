from fastapi import APIRouter, HTTPException
from typing import Sequence
from headhunter_backend.api.dependencies import SessionDep
from headhunter_backend.api.schemas import ApplicationAPISchema
from headhunter_backend.db.crud import list_applications, get_application_by_id
from headhunter_backend.db.models import ApplicationORM
from headhunter_backend.db.converters import application_to_schema

applications_router = APIRouter(
    prefix="/applications",
    tags=["applications"],
    responses={404: {"description": "Not found"}},
)


@applications_router.get("")
async def applications(session: SessionDep) -> Sequence[ApplicationAPISchema]:
    applications: Sequence[ApplicationORM] = await list_applications(session=session)
    return [application_to_schema(orm=application) for application in applications]


@applications_router.get("/{application_id}")
async def get_application(
    application_id: int, session: SessionDep
) -> ApplicationAPISchema:
    application: ApplicationORM | None = await get_application_by_id(
        session=session, application_id=application_id
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application_to_schema(orm=application)
