from enum import Enum


class ContextSourceKind(str, Enum):
    GITHUB = "github"
    WEB = "web"
    YOUTRACK = "youtrack"


class ContextSourceStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    ERROR = "error"
