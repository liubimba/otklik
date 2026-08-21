from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit

import httpx
from selectolax.parser import HTMLParser

from otklik_backend.core.context_source import ContextSourceKind

SOURCE_CONTENT_LIMIT = 8000
GITHUB_README_COUNT = 3
GITHUB_README_EXCERPT_LIMIT = 800
YOUTRACK_NON_JSON_ERROR = (
    "YouTrack не вернул JSON — проверьте базовый URL: это адрес инстанса YouTrack "
    "(например https://host/youtrack), без «/issues» и без параметров запроса в конце."
)
GITHUB_HOSTS = {"github.com", "www.github.com"}


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


class GitHubSourceFetcher:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @staticmethod
    def _parse_user(url: str) -> str:
        path = urlsplit(url).path.strip("/")
        segment = path.split("/")[0] if path else ""
        return segment.removesuffix(".git")

    async def fetch(self, url: str) -> FetchedSource:
        user = self._parse_user(url)
        profile_response = await self._client.get(
            f"https://api.github.com/users/{user}", timeout=15.0
        )
        profile_response.raise_for_status()
        bio = profile_response.json().get("bio") or ""

        repos_response = await self._client.get(
            f"https://api.github.com/users/{user}/repos",
            params={"sort": "updated", "per_page": 30},
            timeout=15.0,
        )
        repos_response.raise_for_status()
        repos = repos_response.json()

        top_repos = sorted(
            repos, key=lambda repo: repo.get("stargazers_count") or 0, reverse=True
        )[:GITHUB_README_COUNT]

        readmes: dict[str, str] = {}
        for repo in top_repos:
            readme_response = await self._client.get(
                f"https://api.github.com/repos/{user}/{repo['name']}/readme",
                headers={"Accept": "application/vnd.github.raw"},
                timeout=15.0,
            )
            if readme_response.is_success:
                readmes[repo["name"]] = readme_response.text.strip()[
                    :GITHUB_README_EXCERPT_LIMIT
                ]

        lines = [bio] if bio else []
        for repo in repos:
            name = repo.get("name", "")
            description = repo.get("description") or ""
            language = repo.get("language") or ""
            stars = repo.get("stargazers_count") or 0
            lines.append(f"{name} — {description} [{language}, ★{stars}]")

        for repo in top_repos:
            name = repo.get("name", "")
            if name in readmes:
                lines.append(readmes[name])

        content = "\n".join(lines)
        return FetchedSource(content=content[:SOURCE_CONTENT_LIMIT])


YOUTRACK_EDGE_COUNT = 10


class YouTrackSourceFetcher:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(self, *, base_url: str, token: str, query: str) -> FetchedSource:
        base = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        earliest = await self._issues(base, headers, query, direction="asc")
        recent = await self._issues(base, headers, query, direction="desc")
        seen = {i.get("idReadable") for i in earliest}
        recent_unique = [i for i in recent if i.get("idReadable") not in seen]
        distinct = len(seen | {i.get("idReadable") for i in recent})
        total = await self._count(base, headers, query, fallback=distinct)

        sections = [f"Задач по запросу '{query}': {total}."]
        if earliest:
            sections.append("Самые ранние:")
            sections.extend(self._line(i) for i in earliest)
        if recent_unique:
            sections.append("Недавние:")
            sections.extend(self._line(i) for i in recent_unique)
        text = "\n".join(sections).strip()
        return FetchedSource(content=text[:SOURCE_CONTENT_LIMIT])

    async def _issues(
        self, base: str, headers: dict[str, str], query: str, *, direction: str
    ) -> list[dict[str, object]]:
        response = await self._client.get(
            f"{base}/api/issues",
            params={
                "query": f"{query} sort by: created {direction}",
                "fields": "idReadable,summary,created",
                "$top": YOUTRACK_EDGE_COUNT,
            },
            headers=headers,
            follow_redirects=True,
            timeout=15.0,
        )
        response.raise_for_status()
        try:
            issues = response.json()
        except ValueError:
            raise ValueError(YOUTRACK_NON_JSON_ERROR)
        if not isinstance(issues, list):
            raise ValueError(YOUTRACK_NON_JSON_ERROR)
        return issues

    @staticmethod
    def _line(issue: dict[str, object]) -> str:
        idr = str(issue.get("idReadable", ""))
        summary = str(issue.get("summary", ""))
        created = issue.get("created")
        date = ""
        if isinstance(created, (int, float)):
            date = datetime.fromtimestamp(created / 1000, tz=UTC).strftime("%Y-%m-%d")
        head = f"- {idr} ({date})" if date else f"- {idr}"
        return f"{head} {summary}".strip()

    async def _count(
        self, base: str, headers: dict[str, str], query: str, *, fallback: int
    ) -> int:
        try:
            response = await self._client.post(
                f"{base}/api/issuesGetter/count",
                params={"fields": "count"},
                json={"query": query},
                headers=headers,
                follow_redirects=True,
                timeout=15.0,
            )
            if not response.is_success:
                return fallback
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return fallback
        if not isinstance(payload, dict):
            return fallback
        count = payload.get("count")
        if isinstance(count, int) and count >= 0:
            return count
        return fallback


def detect_kind(url: str) -> ContextSourceKind:
    host = urlsplit(url).hostname or ""
    if host.lower() in GITHUB_HOSTS:
        return ContextSourceKind.GITHUB
    return ContextSourceKind.WEB


class SourceFetcherRegistry:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def for_url(self, url: str) -> SourceFetcher:
        if detect_kind(url) is ContextSourceKind.GITHUB:
            return GitHubSourceFetcher(self._client)
        return WebPageSourceFetcher(self._client)

    def youtrack_fetcher(self) -> YouTrackSourceFetcher:
        return YouTrackSourceFetcher(self._client)

    async def aclose(self) -> None:
        await self._client.aclose()
