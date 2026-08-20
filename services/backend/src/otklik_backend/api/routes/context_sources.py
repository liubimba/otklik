from fastapi import APIRouter, HTTPException, status

from otklik_backend.api.dependencies import ContextSourceServiceDep
from otklik_backend.api.schemas import (
    ContextSourceAPISchema,
    ContextSourceUpdateAPISchema,
    ContextSourceWriteAPISchema,
)
from otklik_backend.db.converters import context_source_to_schema
from otklik_backend.sources.fetchers import detect_kind

context_sources_router = APIRouter(prefix="/context-sources", tags=["context-sources"])


@context_sources_router.get("")
async def list_context_sources(
    service: ContextSourceServiceDep,
) -> list[ContextSourceAPISchema]:
    sources = await service.list()
    return [context_source_to_schema(source) for source in sources]


@context_sources_router.post("", status_code=status.HTTP_201_CREATED)
async def create_context_source(
    body: ContextSourceWriteAPISchema,
    service: ContextSourceServiceDep,
) -> ContextSourceAPISchema:
    source = await service.add(
        label=body.label,
        url=body.url,
        description=body.description,
        kind=detect_kind(body.url),
    )
    return context_source_to_schema(source)


@context_sources_router.patch("/{source_id}")
async def update_context_source(
    source_id: int,
    body: ContextSourceUpdateAPISchema,
    service: ContextSourceServiceDep,
) -> ContextSourceAPISchema:
    source = await service.update(
        source_id, label=body.label, url=body.url, description=body.description
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Context source not found")
    return context_source_to_schema(source)


@context_sources_router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_context_source(
    source_id: int,
    service: ContextSourceServiceDep,
) -> None:
    deleted = await service.delete(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Context source not found")


@context_sources_router.post("/{source_id}/refresh")
async def refresh_context_source(
    source_id: int,
    service: ContextSourceServiceDep,
) -> ContextSourceAPISchema:
    source = await service.refresh(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Context source not found")
    return context_source_to_schema(source)


@context_sources_router.post("/refresh")
async def refresh_all_context_sources(
    service: ContextSourceServiceDep,
) -> dict[str, int]:
    refreshed = await service.refresh_all()
    return {"refreshed": refreshed}
