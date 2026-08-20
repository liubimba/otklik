from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.ai.source_tools import LLMSource
from otklik_backend.core.context_source import ContextSourceKind, ContextSourceStatus
from otklik_backend.db.models import ContextSourceORM
from otklik_backend.db.repositories.context_sources import ContextSourceRepository
from otklik_backend.log import get_logger
from otklik_backend.secrets.store import SecretStore, context_source_account_for
from otklik_backend.sources.fetchers import SourceFetcherRegistry

EMPTY_SNAPSHOT_ERROR = (
    "Страница не отдала текст — возможно, требует входа или рендерится через JS."
)


class ContextSourceService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        registry: SourceFetcherRegistry,
        secret_store: SecretStore,
    ) -> None:
        self._session_maker = session_maker
        self._registry = registry
        self._secret_store = secret_store
        self._log = get_logger(__name__)

    async def aclose(self) -> None:
        await self._registry.aclose()

    async def add(
        self,
        *,
        label: str,
        description: str | None,
        kind: ContextSourceKind,
        url: str | None = None,
        config: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> ContextSourceORM:
        resolved_url = url if url is not None else (config or {}).get("base_url", "")
        async with self._session_maker() as session:
            source = await ContextSourceRepository.create(
                session=session,
                label=label,
                url=resolved_url,
                description=description,
                kind=kind,
                config=config,
            )
            source_id = source.id
        if token is not None:
            await self._secret_store.set(context_source_account_for(source_id), token)
        return await self._fetch_into(source_id)

    async def refresh(self, source_id: int) -> ContextSourceORM | None:
        async with self._session_maker() as session:
            source = await ContextSourceRepository.get_by_id(
                session=session, source_id=source_id
            )
            if source is None:
                return None
        return await self._fetch_into(source_id)

    async def refresh_all(self) -> int:
        async with self._session_maker() as session:
            sources = await ContextSourceRepository.list_all(session=session)
            ids = [source.id for source in sources]
        for source_id in ids:
            await self._fetch_into(source_id)
        return len(ids)

    async def list_ok_for_llm(self) -> list[LLMSource]:
        async with self._session_maker() as session:
            rows = await ContextSourceRepository.list_ok(session=session)
        return [
            LLMSource(
                id=row.id,
                label=row.label,
                description=row.description,
                url=row.url,
                content=row.content or "",
            )
            for row in rows
        ]

    async def list(self) -> Sequence[ContextSourceORM]:
        async with self._session_maker() as session:
            return await ContextSourceRepository.list_all(session=session)

    async def get(self, source_id: int) -> ContextSourceORM | None:
        async with self._session_maker() as session:
            return await ContextSourceRepository.get_by_id(
                session=session, source_id=source_id
            )

    async def update(
        self,
        source_id: int,
        *,
        label: str,
        description: str | None,
        url: str | None = None,
        config: dict[str, Any] | None = None,
        token: str | None = None,
        clear_token: bool = False,
    ) -> ContextSourceORM | None:
        async with self._session_maker() as session:
            existing = await ContextSourceRepository.get_by_id(
                session=session, source_id=source_id
            )
            if existing is None:
                return None
            resolved_url = url if url is not None else existing.url
            resolved_config = config if config is not None else existing.config
            needs_refetch = (
                resolved_url != existing.url
                or resolved_config != existing.config
                or token is not None
                or clear_token
            )
            updated = await ContextSourceRepository.update_fields(
                session=session,
                source_id=source_id,
                label=label,
                url=resolved_url,
                description=description,
                config=resolved_config,
            )
            if updated is None:
                return None
        account = context_source_account_for(source_id)
        if clear_token:
            await self._secret_store.delete(account)
        elif token is not None:
            await self._secret_store.set(account, token)
        if not needs_refetch:
            return updated
        return await self._fetch_into(source_id)

    async def delete(self, source_id: int) -> bool:
        await self._secret_store.delete(context_source_account_for(source_id))
        async with self._session_maker() as session:
            return await ContextSourceRepository.delete(
                session=session, source_id=source_id
            )

    async def _fetch_into(self, source_id: int) -> ContextSourceORM:
        async with self._session_maker() as session:
            row = await ContextSourceRepository.get_by_id(
                session=session, source_id=source_id
            )
        if row is None:
            raise RuntimeError(f"context source {source_id} disappeared during fetch")
        try:
            if row.kind is ContextSourceKind.YOUTRACK:
                token = (
                    await self._secret_store.get(context_source_account_for(source_id))
                    or ""
                )
                cfg = row.config or {}
                fetched = await self._registry.youtrack_fetcher().fetch(
                    base_url=cfg.get("base_url", ""),
                    token=token,
                    query=cfg.get("query", ""),
                )
            else:
                fetcher = self._registry.for_url(row.url)
                fetched = await fetcher.fetch(row.url)
        except Exception as e:
            async with self._session_maker() as session:
                result = await ContextSourceRepository.set_snapshot(
                    session=session,
                    source_id=source_id,
                    content=None,
                    status=ContextSourceStatus.ERROR,
                    error=str(e),
                )
        else:
            if fetched.content.strip():
                async with self._session_maker() as session:
                    result = await ContextSourceRepository.set_snapshot(
                        session=session,
                        source_id=source_id,
                        content=fetched.content,
                        status=ContextSourceStatus.OK,
                        error=None,
                    )
            else:
                async with self._session_maker() as session:
                    result = await ContextSourceRepository.set_snapshot(
                        session=session,
                        source_id=source_id,
                        content=None,
                        status=ContextSourceStatus.ERROR,
                        error=EMPTY_SNAPSHOT_ERROR,
                    )
        if result is None:
            raise RuntimeError(f"context source {source_id} disappeared during fetch")
        return result
