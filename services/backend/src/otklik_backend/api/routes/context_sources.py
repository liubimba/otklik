from fastapi import APIRouter, HTTPException, status

from otklik_backend.api.dependencies import ContextSourceServiceDep, SecretStoreDep
from otklik_backend.api.schemas import (
    ContextSourceAPISchema,
    ContextSourceUpdateAPISchema,
    ContextSourceWriteAPISchema,
)
from otklik_backend.core.context_source import ContextSourceKind
from otklik_backend.db.converters import context_source_to_schema
from otklik_backend.secrets.store import SecretStore, context_source_account_for

context_sources_router = APIRouter(prefix="/context-sources", tags=["context-sources"])


async def _has_token(store: SecretStore, source_id: int) -> bool:
    return await store.get(context_source_account_for(source_id)) is not None


@context_sources_router.get("")
async def list_context_sources(
    service: ContextSourceServiceDep,
    secret_store: SecretStoreDep,
) -> list[ContextSourceAPISchema]:
    sources = await service.list()
    return [
        context_source_to_schema(
            source, has_token=await _has_token(secret_store, source.id)
        )
        for source in sources
    ]


@context_sources_router.post("", status_code=status.HTTP_201_CREATED)
async def create_context_source(
    body: ContextSourceWriteAPISchema,
    service: ContextSourceServiceDep,
    secret_store: SecretStoreDep,
) -> ContextSourceAPISchema:
    if body.kind is ContextSourceKind.YOUTRACK and not body.token:
        raise HTTPException(status_code=422, detail="token required for youtrack")
    source = await service.add(
        label=body.label,
        url=body.url,
        description=body.description,
        kind=body.kind,
        config=body.config,
        token=body.token,
    )
    return context_source_to_schema(
        source, has_token=await _has_token(secret_store, source.id)
    )


@context_sources_router.patch("/{source_id}")
async def update_context_source(
    source_id: int,
    body: ContextSourceUpdateAPISchema,
    service: ContextSourceServiceDep,
    secret_store: SecretStoreDep,
) -> ContextSourceAPISchema:
    source = await service.update(
        source_id,
        label=body.label,
        description=body.description,
        url=body.url,
        config=body.config,
        token=body.token,
        clear_token=body.clear_token,
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Context source not found")
    return context_source_to_schema(
        source, has_token=await _has_token(secret_store, source.id)
    )


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
    secret_store: SecretStoreDep,
) -> ContextSourceAPISchema:
    source = await service.refresh(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Context source not found")
    return context_source_to_schema(
        source, has_token=await _has_token(secret_store, source.id)
    )


@context_sources_router.post("/refresh")
async def refresh_all_context_sources(
    service: ContextSourceServiceDep,
) -> dict[str, int]:
    refreshed = await service.refresh_all()
    return {"refreshed": refreshed}
