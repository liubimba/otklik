from datetime import datetime

import pytest
from pydantic import ValidationError

from otklik_backend.core.context_source import ContextSourceKind, ContextSourceStatus
from otklik_backend.db.converters import context_source_to_schema
from otklik_backend.db.models import ContextSourceORM
from otklik_backend.api.schemas import ContextSourceWriteAPISchema


def test_context_source_to_schema_maps_fields_and_omits_content() -> None:
    orm = ContextSourceORM(
        id=1,
        label="My GitHub",
        url="https://github.com/octocat",
        description="octocat's profile",
        kind=ContextSourceKind.GITHUB,
        content="raw fetched content",
        status=ContextSourceStatus.OK,
        error=None,
        fetched_at=datetime(2026, 8, 18, 10, 0, 0),
        created_at=datetime(2026, 8, 18, 9, 0, 0),
        config=None,
    )

    schema = context_source_to_schema(orm=orm)

    assert schema.id == 1
    assert schema.label == "My GitHub"
    assert schema.url == "https://github.com/octocat"
    assert schema.description == "octocat's profile"
    assert schema.kind == ContextSourceKind.GITHUB
    assert schema.status == ContextSourceStatus.OK
    assert schema.error is None
    assert schema.fetched_at == datetime(2026, 8, 18, 10, 0, 0)
    assert schema.created_at == datetime(2026, 8, 18, 9, 0, 0)
    assert schema.config is None
    assert schema.has_token is False
    assert not hasattr(schema, "content")
    assert not hasattr(schema, "token")


def test_context_source_to_schema_maps_config_and_has_token() -> None:
    orm = ContextSourceORM(
        id=2,
        label="My YouTrack",
        url="",
        description=None,
        kind=ContextSourceKind.YOUTRACK,
        content=None,
        status=ContextSourceStatus.PENDING,
        error=None,
        fetched_at=None,
        created_at=datetime(2026, 8, 18, 9, 0, 0),
        config={"base_url": "https://yt.example.com", "query": "for: me"},
    )

    schema = context_source_to_schema(orm=orm, has_token=True)

    assert schema.config == {"base_url": "https://yt.example.com", "query": "for: me"}
    assert schema.has_token is True
    assert not hasattr(schema, "content")
    assert not hasattr(schema, "token")


def test_context_source_write_schema_accepts_https_url_for_web() -> None:
    schema = ContextSourceWriteAPISchema(
        label="My GitHub",
        kind=ContextSourceKind.WEB,
        url="https://github.com/octocat",
        description=None,
    )

    assert schema.url == "https://github.com/octocat"


def test_context_source_write_schema_accepts_http_url_for_web() -> None:
    schema = ContextSourceWriteAPISchema(
        label="My Site",
        kind=ContextSourceKind.WEB,
        url="http://example.com",
        description=None,
    )

    assert schema.url == "http://example.com"


def test_context_source_write_schema_rejects_bare_string_for_web() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(
            label="Bad", kind=ContextSourceKind.WEB, url="not-a-url", description=None
        )


def test_context_source_write_schema_rejects_ftp_url_for_web() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(
            label="Bad",
            kind=ContextSourceKind.WEB,
            url="ftp://example.com/file",
            description=None,
        )


def test_context_source_write_schema_rejects_missing_url_for_web() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(label="Bad", kind=ContextSourceKind.WEB, url=None)


def test_context_source_write_schema_rejects_config_for_web() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(
            label="Bad",
            kind=ContextSourceKind.WEB,
            url="https://example.com",
            config={"base_url": "https://example.com", "query": "x"},
        )


def test_context_source_write_schema_accepts_youtrack_config() -> None:
    schema = ContextSourceWriteAPISchema(
        label="My YouTrack",
        kind=ContextSourceKind.YOUTRACK,
        config={"base_url": "https://yt.example.com", "query": "for: me"},
        token="secret-token",
    )

    assert schema.config == {"base_url": "https://yt.example.com", "query": "for: me"}
    assert schema.token == "secret-token"


def test_context_source_write_schema_rejects_youtrack_missing_config() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(label="Bad", kind=ContextSourceKind.YOUTRACK)


def test_context_source_write_schema_rejects_youtrack_missing_base_url() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(
            label="Bad", kind=ContextSourceKind.YOUTRACK, config={"query": "for: me"}
        )


def test_context_source_write_schema_rejects_youtrack_missing_query() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(
            label="Bad",
            kind=ContextSourceKind.YOUTRACK,
            config={"base_url": "https://yt.example.com"},
        )


def test_context_source_write_schema_rejects_youtrack_invalid_base_url() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(
            label="Bad",
            kind=ContextSourceKind.YOUTRACK,
            config={"base_url": "not-a-url", "query": "for: me"},
        )
