from enum import Enum


class ContextSourceKind(str, Enum):
    GITHUB = "github"
    WEB = "web"


class ContextSourceStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    ERROR = "error"
