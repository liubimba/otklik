from dataclasses import dataclass
from typing import Protocol

import httpx
from selectolax.parser import HTMLParser

SOURCE_CONTENT_LIMIT = 8000


@dataclass(frozen=True)
class FetchedSource:
    content: str


class SourceFetcher(Protocol):
    async def fetch(self, url: str) -> FetchedSource: ...


class WebPageSourceFetcher:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(self, url: str) -> FetchedSource:
        response = await self._client.get(url, follow_redirects=True, timeout=15.0)
        response.raise_for_status()
        tree = HTMLParser(response.text)
        for tag in tree.css("script, style, nav, header, footer, noscript"):
            tag.decompose()
        body = tree.body or tree.root
        text = body.text(separator=" ", strip=True) if body else ""
        text = " ".join(text.split())
        return FetchedSource(content=text[:SOURCE_CONTENT_LIMIT])
