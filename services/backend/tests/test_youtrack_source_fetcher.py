import httpx
import pytest

from otklik_backend.sources.fetchers import (
    SOURCE_CONTENT_LIMIT,
    SourceFetcherRegistry,
    YouTrackSourceFetcher,
)

ISSUES = [
    {"idReadable": "PRJ-1", "summary": "Fix login bug"},
    {"idReadable": "PRJ-2", "summary": "Add dark mode"},
    {"idReadable": "PRJ-3", "summary": "Improve onboarding"},
]


def make_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def make_handler(recorded_requests, status_code=200, body=ISSUES):
    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        if request.url.path == "/api/issues":
            return httpx.Response(status_code, json=body)
        raise AssertionError(f"unexpected path {request.url.path}")

    return handler


async def test_fetch_composes_count_and_issue_lines_from_youtrack_api():
    recorded_requests: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(client=make_client(make_handler(recorded_requests)))

    result = await fetcher.fetch(
        base_url="https://yt.example.com/", token="secret-token", query="project: PRJ"
    )

    assert "Задач по запросу 'project: PRJ': 3." in result.content
    assert "PRJ-1 Fix login bug" in result.content
    assert "PRJ-2 Add dark mode" in result.content
    assert "PRJ-3 Improve onboarding" in result.content

    assert len(recorded_requests) == 1
    request = recorded_requests[0]
    assert request.headers["Authorization"] == "Bearer secret-token"
    assert request.url.params["query"] == "project: PRJ"


async def test_fetch_strips_trailing_slash_from_base_url():
    recorded_requests: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(client=make_client(make_handler(recorded_requests)))

    await fetcher.fetch(
        base_url="https://yt.example.com/", token="secret-token", query="project: PRJ"
    )

    request = recorded_requests[0]
    assert request.url.path == "/api/issues"


async def test_fetch_truncates_content_to_source_content_limit():
    huge_issues = [{"idReadable": f"PRJ-{i}", "summary": "x" * 1000} for i in range(30)]
    recorded_requests: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(
        client=make_client(make_handler(recorded_requests, body=huge_issues))
    )

    result = await fetcher.fetch(
        base_url="https://yt.example.com", token="secret-token", query="project: PRJ"
    )

    assert len(result.content) == SOURCE_CONTENT_LIMIT


async def test_fetch_raises_on_unauthorized_response():
    recorded_requests: list[httpx.Request] = []
    fetcher = YouTrackSourceFetcher(
        client=make_client(make_handler(recorded_requests, status_code=401, body={}))
    )

    with pytest.raises(httpx.HTTPStatusError):
        await fetcher.fetch(
            base_url="https://yt.example.com",
            token="bad-token",
            query="project: PRJ",
        )


def test_registry_returns_youtrack_fetcher():
    registry = SourceFetcherRegistry(client=httpx.AsyncClient())
    fetcher = registry.youtrack_fetcher()
    assert isinstance(fetcher, YouTrackSourceFetcher)


def make_html_handler():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<!DOCTYPE html><html><body>Login</body></html>",
            headers={"content-type": "text/html"},
        )

    return handler


def make_json_object_handler():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "Unauthorized"})

    return handler


async def test_fetch_raises_clear_error_on_html_response():
    from otklik_backend.sources.fetchers import YOUTRACK_NON_JSON_ERROR

    fetcher = YouTrackSourceFetcher(client=make_client(make_html_handler()))

    with pytest.raises(ValueError) as excinfo:
        await fetcher.fetch(
            base_url="https://yt.example.com/issues/issues",
            token="secret-token",
            query="for: me",
        )
    assert str(excinfo.value) == YOUTRACK_NON_JSON_ERROR


async def test_fetch_raises_clear_error_when_response_is_not_a_list():
    from otklik_backend.sources.fetchers import YOUTRACK_NON_JSON_ERROR

    fetcher = YouTrackSourceFetcher(client=make_client(make_json_object_handler()))

    with pytest.raises(ValueError) as excinfo:
        await fetcher.fetch(
            base_url="https://yt.example.com", token="secret-token", query="for: me"
        )
    assert str(excinfo.value) == YOUTRACK_NON_JSON_ERROR
