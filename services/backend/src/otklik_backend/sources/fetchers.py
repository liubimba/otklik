from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

import httpx
from selectolax.parser import HTMLParser

from otklik_backend.core.context_source import ContextSourceKind

SOURCE_CONTENT_LIMIT = 8000
GITHUB_README_COUNT = 3
GITHUB_README_EXCERPT_LIMIT = 800
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
