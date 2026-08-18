from otklik_backend.ai.source_tools import LLMSource, SourceToolProvider


def _sources() -> list[LLMSource]:
    return [
        LLMSource(
            id=1,
            label="My GitHub",
            description="Personal projects",
            url="https://github.com/octocat",
            content="README content for octocat",
        ),
        LLMSource(
            id=2,
            label="Portfolio",
            description=None,
            url="https://example.com/portfolio",
            content="Portfolio snapshot text",
        ),
    ]


def test_available_text_lists_ids_and_labels_without_content() -> None:
    provider = SourceToolProvider(_sources())

    text = provider.available_text()

    assert "id=1" in text
    assert "My GitHub" in text
    assert "id=2" in text
    assert "Portfolio" in text
    assert "Portfolio snapshot text" not in text
    assert "README content for octocat" not in text


def test_available_text_uses_dash_placeholder_for_missing_description() -> None:
    provider = SourceToolProvider(_sources())

    text = provider.available_text()

    assert "—" in text


def test_snapshots_text_contains_source_content() -> None:
    provider = SourceToolProvider(_sources())

    text = provider.snapshots_text()

    assert "Portfolio snapshot text" in text
    assert "README content for octocat" in text
    assert "My GitHub" in text
    assert "https://github.com/octocat" in text


def test_tool_param_is_named_fetch_source_with_integer_source_id() -> None:
    provider = SourceToolProvider(_sources())

    tool = provider.tool_param()

    assert tool["type"] == "function"
    assert tool["function"]["name"] == "fetch_source"
    params = tool["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"]["source_id"]["type"] == "integer"
    assert "source_id" in params["required"]


def test_execute_returns_matching_source_content() -> None:
    provider = SourceToolProvider(_sources())

    result = provider.execute("fetch_source", '{"source_id": 2}')

    assert result == "Portfolio snapshot text"


def test_execute_returns_not_found_note_for_missing_source() -> None:
    provider = SourceToolProvider(_sources())

    result = provider.execute("fetch_source", '{"source_id": 999}')

    assert result == "Источник не найден."


def test_execute_returns_note_for_unknown_tool_name() -> None:
    provider = SourceToolProvider(_sources())

    result = provider.execute("nope", "{}")

    assert "nope" in result
    assert "Unknown tool" in result


def test_execute_handles_malformed_json_without_raising() -> None:
    provider = SourceToolProvider(_sources())

    result = provider.execute("fetch_source", "{bad")

    assert isinstance(result, str)
    assert result != ""


def test_execute_handles_missing_source_id_key() -> None:
    provider = SourceToolProvider(_sources())

    result = provider.execute("fetch_source", "{}")

    assert isinstance(result, str)
    assert result != ""
