from collections.abc import Sequence

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.ai.source_tools import LLMSource
from otklik_backend.core.context_source import ContextSourceStatus
from otklik_backend.db.models import ContextSourceORM
from otklik_backend.db.repositories.context_sources import ContextSourceRepository
from otklik_backend.log import get_logger
from otklik_backend.sources.fetchers import SourceFetcherRegistry, detect_kind


class ContextSourceService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        registry: SourceFetcherRegistry,
    ) -> None:
        self._session_maker = session_maker
        self._registry = registry

    async def aclose(self) -> None:
        await self._registry.aclose()
        self._log = get_logger(__name__)

    async def add(
        self, *, label: str, url: str, description: str | None
    ) -> ContextSourceORM:
        kind = detect_kind(url)
        async with self._session_maker() as session:
            source = await ContextSourceRepository.create(
                session=session,
                label=label,
                url=url,
                description=description,
                kind=kind,
            )
            source_id = source.id
        return await self._fetch_into(source_id, url)

    async def refresh(self, source_id: int) -> ContextSourceORM | None:
        async with self._session_maker() as session:
            source = await ContextSourceRepository.get_by_id(
                session=session, source_id=source_id
            )
            if source is None:
                return None
            url = source.url
        return await self._fetch_into(source_id, url)

    async def refresh_all(self) -> int:
        async with self._session_maker() as session:
            sources = await ContextSourceRepository.list_all(session=session)
            targets = [(source.id, source.url) for source in sources]
        for source_id, url in targets:
            await self._fetch_into(source_id, url)
        return len(targets)

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

    async def update(
        self, source_id: int, *, label: str, url: str, description: str | None
    ) -> ContextSourceORM | None:
        async with self._session_maker() as session:
            existing = await ContextSourceRepository.get_by_id(
                session=session, source_id=source_id
            )
            if existing is None:
                return None
            url_changed = existing.url != url
            updated = await ContextSourceRepository.update_fields(
                session=session,
                source_id=source_id,
                label=label,
                url=url,
                description=description,
            )
            if updated is None:
                return None
            if url_changed:
                updated = await ContextSourceRepository.set_kind(
                    session=session, source_id=source_id, kind=detect_kind(url)
                )
                if updated is None:
                    return None
        if url_changed:
            return await self._fetch_into(source_id, url)
        return updated

    async def delete(self, source_id: int) -> bool:
        async with self._session_maker() as session:
            return await ContextSourceRepository.delete(
                session=session, source_id=source_id
            )

    async def _fetch_into(self, source_id: int, url: str) -> ContextSourceORM:
        fetcher = self._registry.for_url(url)
        try:
            fetched = await fetcher.fetch(url)
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
            async with self._session_maker() as session:
                result = await ContextSourceRepository.set_snapshot(
                    session=session,
                    source_id=source_id,
                    content=fetched.content,
                    status=ContextSourceStatus.OK,
                    error=None,
                )
        if result is None:
            raise RuntimeError(f"context source {source_id} disappeared during fetch")
        return result
