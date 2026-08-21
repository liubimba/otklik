from datetime import datetime, timezone

import httpx
import pytest

from otklik_backend.sources.fetchers import (
    SOURCE_CONTENT_LIMIT,
    SourceFetcherRegistry,
    YouTrackSourceFetcher,
)


def ms(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)


EARLIEST = [
    {"idReadable": "WCS-100", "summary": "Первая задача", "created": ms(2019, 5, 14)},
    {"idReadable": "WCS-101", "summary": "Вторая задача", "created": ms(2019, 6, 1)},
]
RECENT = [
    {"idReadable": "WCS-5059", "summary": "Свежая задача", "created": ms(2026, 8, 19)},
    {"idReadable": "WCS-5012", "summary": "Почти свежая", "created": ms(2026, 8, 10)},
]


def make_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def make_handler(recorded_requests, *, count=112):
    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        if request.url.path == "/api/issuesGetter/count":
            return httpx.Response(200, json={"count": count})
        if request.url.path == "/api/issues":
            query = request.url.params.get("query", "")
            body = EARLIEST if "asc" in query else RECENT
            return httpx.Response(200, json=body)
        raise AssertionError(f"unexpected path {request.url.path}")

    return handler


async def test_snapshot_carries_true_count_earliest_and_recent_with_dates():
    recorded: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(
        client=make_client(make_handler(recorded, count=112))
    )

    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert "Задач по запросу 'for: me': 112." in result.content
    assert "Самые ранние:" in result.content
    assert "- WCS-100 (2019-05-14) Первая задача" in result.content
    assert "Недавние:" in result.content
    assert "- WCS-5059 (2026-08-19) Свежая задача" in result.content


async def test_fetch_sorts_by_creation_ascending_and_descending():
    recorded: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(client=make_client(make_handler(recorded)))

    await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    issue_queries = [
        r.url.params.get("query", "") for r in recorded if r.url.path == "/api/issues"
    ]
    assert any("created asc" in q for q in issue_queries)
    assert any("created desc" in q for q in issue_queries)


async def test_recent_section_omitted_when_it_only_repeats_the_earliest():
    only = [
        {"idReadable": "WCS-1", "summary": "Единственная", "created": ms(2020, 1, 1)},
        {"idReadable": "WCS-2", "summary": "Вторая", "created": ms(2020, 2, 1)},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/issuesGetter/count":
            return httpx.Response(200, json={"count": 2})
        if request.url.path == "/api/issues":
            query = request.url.params.get("query", "")
            body = only if "asc" in query else list(reversed(only))
            return httpx.Response(200, json=body)
        raise AssertionError(f"unexpected path {request.url.path}")

    fetcher = YouTrackSourceFetcher(client=make_client(handler))
    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert "Недавние:" not in result.content
    assert result.content.count("WCS-1") == 1
    assert result.content.count("WCS-2") == 1


async def test_count_falls_back_to_fetched_issues_when_count_endpoint_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/issuesGetter/count":
            return httpx.Response(404, json={"error": "Not Found"})
        if request.url.path == "/api/issues":
            query = request.url.params.get("query", "")
            body = EARLIEST if "asc" in query else RECENT
            return httpx.Response(200, json=body)
        raise AssertionError(f"unexpected path {request.url.path}")

    fetcher = YouTrackSourceFetcher(client=make_client(handler))
    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert "Задач по запросу 'for: me': 4." in result.content


async def test_line_omits_date_when_created_is_missing():
    undated = [{"idReadable": "WCS-9", "summary": "Без даты"}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/issuesGetter/count":
            return httpx.Response(200, json={"count": 1})
        if request.url.path == "/api/issues":
            return httpx.Response(200, json=undated)
        raise AssertionError(f"unexpected path {request.url.path}")

    fetcher = YouTrackSourceFetcher(client=make_client(handler))
    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert "- WCS-9 Без даты" in result.content
    assert "(" not in result.content.split("WCS-9")[1].split("\n")[0]


async def test_fetch_strips_trailing_slash_from_base_url():
    recorded: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(client=make_client(make_handler(recorded)))

    await fetcher.fetch(
        base_url="https://yt.example.com/", token="secret-token", query="for: me"
    )

    paths = {r.url.path for r in recorded}
    assert paths == {"/api/issues", "/api/issuesGetter/count"}


async def test_fetch_sends_bearer_token():
    recorded: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(client=make_client(make_handler(recorded)))

    await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert all(r.headers["Authorization"] == "Bearer secret-token" for r in recorded)


async def test_fetch_truncates_content_to_source_content_limit():
    huge = [
        {"idReadable": f"WCS-{i}", "summary": "x" * 1000, "created": ms(2020, 1, 1)}
        for i in range(30)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/issuesGetter/count":
            return httpx.Response(200, json={"count": 30})
        if request.url.path == "/api/issues":
            return httpx.Response(200, json=huge)
        raise AssertionError(f"unexpected path {request.url.path}")

    fetcher = YouTrackSourceFetcher(client=make_client(handler))
    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert len(result.content) == SOURCE_CONTENT_LIMIT


async def test_fetch_raises_on_unauthorized_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={})

    fetcher = YouTrackSourceFetcher(client=make_client(handler))

    with pytest.raises(httpx.HTTPStatusError):
        await fetcher.fetch(
            base_url="https://yt.example.com", token="bad-token", query="for: me"
        )


def test_registry_returns_youtrack_fetcher():
    registry = SourceFetcherRegistry(client=httpx.AsyncClient())
    fetcher = registry.youtrack_fetcher()
    assert isinstance(fetcher, YouTrackSourceFetcher)


async def test_fetch_raises_clear_error_on_html_response():
    from otklik_backend.sources.fetchers import YOUTRACK_NON_JSON_ERROR

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<!DOCTYPE html><html><body>Login</body></html>",
            headers={"content-type": "text/html"},
        )

    fetcher = YouTrackSourceFetcher(client=make_client(handler))

    with pytest.raises(ValueError) as excinfo:
        await fetcher.fetch(
            base_url="https://yt.example.com/issues/issues",
            token="secret-token",
            query="for: me",
        )
    assert str(excinfo.value) == YOUTRACK_NON_JSON_ERROR


async def test_fetch_raises_clear_error_when_response_is_not_a_list():
    from otklik_backend.sources.fetchers import YOUTRACK_NON_JSON_ERROR

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "Unauthorized"})

    fetcher = YouTrackSourceFetcher(client=make_client(handler))

    with pytest.raises(ValueError) as excinfo:
        await fetcher.fetch(
            base_url="https://yt.example.com", token="secret-token", query="for: me"
        )
    assert str(excinfo.value) == YOUTRACK_NON_JSON_ERROR
