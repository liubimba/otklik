import httpx

from otklik_backend.sources.fetchers import (
    GITHUB_README_COUNT,
    SOURCE_CONTENT_LIMIT,
    GitHubSourceFetcher,
)

PROFILE = {"bio": "Builder of small useful things."}

REPOS = [
    {
        "name": "alpha",
        "description": "First repo",
        "language": "Python",
        "stargazers_count": 5,
    },
    {
        "name": "beta",
        "description": "Second repo",
        "language": "Rust",
        "stargazers_count": 50,
    },
    {
        "name": "gamma",
        "description": "Third repo",
        "language": "TypeScript",
        "stargazers_count": 20,
    },
    {
        "name": "delta",
        "description": "Fourth repo",
        "language": "Go",
        "stargazers_count": 1,
    },
]

READMES = {
    "beta": "# Beta\nA fast tool written in Rust.",
    "gamma": "# Gamma\nA typed frontend toolkit.",
}


def make_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def make_handler(requested_readme_paths):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/users/octocat":
            return httpx.Response(200, json=PROFILE)
        if path == "/users/octocat/repos":
            return httpx.Response(200, json=REPOS)
        if path.startswith("/repos/octocat/") and path.endswith("/readme"):
            requested_readme_paths.append(path)
            repo = path.split("/")[3]
            if repo not in READMES:
                return httpx.Response(404)
            return httpx.Response(200, text=READMES[repo])
        raise AssertionError(f"unexpected path {path}")

    return handler


async def test_fetch_composes_bio_repo_lines_and_top_readmes():
    requested_readme_paths: list[str] = []
    fetcher = GitHubSourceFetcher(
        client=make_client(make_handler(requested_readme_paths))
    )

    result = await fetcher.fetch("https://github.com/octocat")

    assert "Builder of small useful things." in result.content
    assert "alpha — First repo [Python, ★5]" in result.content
    assert "beta — Second repo [Rust, ★50]" in result.content
    assert "gamma — Third repo [TypeScript, ★20]" in result.content
    assert "delta — Fourth repo [Go, ★1]" in result.content
    assert "A fast tool written in Rust." in result.content
    assert "A typed frontend toolkit." in result.content

    assert len(requested_readme_paths) == GITHUB_README_COUNT
    assert "/repos/octocat/beta/readme" in requested_readme_paths
    assert "/repos/octocat/gamma/readme" in requested_readme_paths
    assert "/repos/octocat/alpha/readme" in requested_readme_paths
    assert "/repos/octocat/delta/readme" not in requested_readme_paths


async def test_fetch_skips_readme_gracefully_on_404_but_keeps_metadata():
    requested_readme_paths: list[str] = []
    fetcher = GitHubSourceFetcher(
        client=make_client(make_handler(requested_readme_paths))
    )

    result = await fetcher.fetch("https://github.com/octocat")

    assert "alpha — First repo [Python, ★5]" in result.content
    assert "/repos/octocat/alpha/readme" in requested_readme_paths


async def test_parse_user_strips_trailing_path_and_suffixes():
    assert GitHubSourceFetcher._parse_user("https://github.com/octocat") == "octocat"
    assert GitHubSourceFetcher._parse_user("https://github.com/octocat/") == "octocat"
    assert (
        GitHubSourceFetcher._parse_user("https://github.com/octocat/some-repo")
        == "octocat"
    )
    assert (
        GitHubSourceFetcher._parse_user("https://github.com/octocat.git") == "octocat"
    )
    assert (
        GitHubSourceFetcher._parse_user("https://github.com/octocat?tab=repositories")
        == "octocat"
    )
    assert (
        GitHubSourceFetcher._parse_user("https://github.com/octocat#readme")
        == "octocat"
    )


async def test_fetch_truncates_content_to_source_content_limit():
    huge_bio = "x" * (SOURCE_CONTENT_LIMIT * 2)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/users/octocat":
            return httpx.Response(200, json={"bio": huge_bio})
        if path == "/users/octocat/repos":
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected path {path}")

    fetcher = GitHubSourceFetcher(client=make_client(handler))

    result = await fetcher.fetch("https://github.com/octocat")

    assert len(result.content) == SOURCE_CONTENT_LIMIT
