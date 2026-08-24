from datetime import datetime, timezone

import httpx
import pytest

from otklik_backend.sources.fetchers import (
    SOURCE_CONTENT_LIMIT,
    YOUTRACK_FETCH_CAP,
    SourceFetcherRegistry,
    YouTrackSourceFetcher,
)


def ms(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)


def make_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def issues_handler(body, recorded=None, status_code=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if recorded is not None:
            recorded.append(request)
        if request.url.path == "/api/issues":
            return httpx.Response(status_code, json=body)
        raise AssertionError(f"unexpected path {request.url.path}")

    return handler


OLDEST = {"idReadable": "WCS-4283", "summary": "Первая", "created": ms(2024, 12, 11)}
NEWEST = {"idReadable": "WCS-5059", "summary": "Свежая", "created": ms(2026, 8, 19)}
MIDDLE = [
    {"idReadable": f"WCS-{4300 + i}", "summary": f"mid{i}", "created": ms(2025, i, 1)}
    for i in range(1, 11)
]
BACKLOG = [NEWEST, *MIDDLE, OLDEST]


async def test_single_fetch_yields_true_count_and_both_ends_sorted_locally():
    fetcher = YouTrackSourceFetcher(client=make_client(issues_handler(BACKLOG)))

    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert "Задач по запросу 'for: me': 12." in result.content
    assert "Самые ранние:" in result.content
    assert "- WCS-4283 (2024-12-11) Первая" in result.content
    assert "Недавние:" in result.content
    assert "- WCS-5059 (2026-08-19) Свежая" in result.content
    assert result.content.count("WCS-4283") == 1
    assert result.content.count("WCS-5059") == 1


async def test_fetch_makes_one_request_pulling_all_issues_with_created():
    recorded: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(
        client=make_client(issues_handler(BACKLOG, recorded))
    )

    await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert len(recorded) == 1
    request = recorded[0]
    assert request.url.path == "/api/issues"
    assert int(request.url.params["$top"]) >= YOUTRACK_FETCH_CAP
    assert "created" in request.url.params["fields"]


async def test_small_backlog_is_listed_once_without_a_recent_section():
    two = [
        {"idReadable": "WCS-1", "summary": "Раз", "created": ms(2020, 1, 1)},
        {"idReadable": "WCS-2", "summary": "Два", "created": ms(2020, 2, 1)},
    ]
    fetcher = YouTrackSourceFetcher(client=make_client(issues_handler(two)))

    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert "Задач по запросу 'for: me': 2." in result.content
    assert "Недавние:" not in result.content
    assert result.content.count("WCS-1") == 1
    assert result.content.count("WCS-2") == 1


async def test_count_reports_at_least_when_the_fetch_cap_is_reached():
    capped = [
        {"idReadable": f"WCS-{i}", "summary": "x", "created": ms(2020, 1, 1)}
        for i in range(YOUTRACK_FETCH_CAP)
    ]
    fetcher = YouTrackSourceFetcher(client=make_client(issues_handler(capped)))

    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert f"Задач по запросу 'for: me': ≥{YOUTRACK_FETCH_CAP}." in result.content


async def test_line_omits_date_when_created_is_missing():
    undated = [{"idReadable": "WCS-9", "summary": "Без даты"}]
    fetcher = YouTrackSourceFetcher(client=make_client(issues_handler(undated)))

    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert "- WCS-9 Без даты" in result.content
    assert "(" not in result.content.split("WCS-9")[1].split("\n")[0]


async def test_fetch_strips_trailing_slash_from_base_url():
    recorded: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(
        client=make_client(issues_handler(BACKLOG, recorded))
    )

    await fetcher.fetch(
        base_url="https://yt.example.com/", token="secret-token", query="for: me"
    )

    assert recorded[0].url.path == "/api/issues"


async def test_fetch_sends_bearer_token():
    recorded: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(
        client=make_client(issues_handler(BACKLOG, recorded))
    )

    await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert recorded[0].headers["Authorization"] == "Bearer secret-token"


async def test_fetch_truncates_content_to_source_content_limit():
    huge = [
        {"idReadable": f"WCS-{i}", "summary": "x" * 1000, "created": ms(2020, 1, i + 1)}
        for i in range(20)
    ]
    fetcher = YouTrackSourceFetcher(client=make_client(issues_handler(huge)))

    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="for: me"
    )

    assert len(result.content) == SOURCE_CONTENT_LIMIT


async def test_fetch_raises_on_unauthorized_response():
    fetcher = YouTrackSourceFetcher(
        client=make_client(issues_handler({}, status_code=401))
    )

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

    fetcher = YouTrackSourceFetcher(
        client=make_client(issues_handler({"error": "Unauthorized"}))
    )

    with pytest.raises(ValueError) as excinfo:
        await fetcher.fetch(
            base_url="https://yt.example.com", token="secret-token", query="for: me"
        )
    assert str(excinfo.value) == YOUTRACK_NON_JSON_ERROR
