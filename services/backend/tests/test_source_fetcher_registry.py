import httpx

from otklik_backend.core.context_source import ContextSourceKind
from otklik_backend.sources.fetchers import (
    GitHubSourceFetcher,
    SourceFetcherRegistry,
    WebPageSourceFetcher,
    detect_kind,
)


def test_detect_kind_returns_github_for_github_host():
    assert detect_kind("https://github.com/liubimba") is ContextSourceKind.GITHUB


def test_detect_kind_returns_web_for_other_hosts():
    assert detect_kind("https://habr.com/ru/articles/1/") is ContextSourceKind.WEB


def test_detect_kind_matches_www_github_host():
    assert detect_kind("https://www.github.com/liubimba") is ContextSourceKind.GITHUB


def test_registry_returns_github_fetcher_for_github_url():
    registry = SourceFetcherRegistry(client=httpx.AsyncClient())
    fetcher = registry.for_url("https://github.com/liubimba")
    assert isinstance(fetcher, GitHubSourceFetcher)


def test_registry_returns_web_fetcher_for_other_url():
    registry = SourceFetcherRegistry(client=httpx.AsyncClient())
    fetcher = registry.for_url("https://habr.com/ru/articles/1/")
    assert isinstance(fetcher, WebPageSourceFetcher)
