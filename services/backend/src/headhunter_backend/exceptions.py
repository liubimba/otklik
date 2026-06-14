from typing import ClassVar


class ServerError(Exception):
    status_code: ClassVar[int]
    detail: ClassVar[str]
