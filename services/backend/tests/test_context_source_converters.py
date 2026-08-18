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
    assert not hasattr(schema, "content")


def test_context_source_write_schema_accepts_https_url() -> None:
    schema = ContextSourceWriteAPISchema(
        label="My GitHub", url="https://github.com/octocat", description=None
    )

    assert schema.url == "https://github.com/octocat"


def test_context_source_write_schema_accepts_http_url() -> None:
    schema = ContextSourceWriteAPISchema(
        label="My Site", url="http://example.com", description=None
    )

    assert schema.url == "http://example.com"


def test_context_source_write_schema_rejects_bare_string() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(label="Bad", url="not-a-url", description=None)


def test_context_source_write_schema_rejects_ftp_url() -> None:
    with pytest.raises(ValidationError):
        ContextSourceWriteAPISchema(
            label="Bad", url="ftp://example.com/file", description=None
        )
