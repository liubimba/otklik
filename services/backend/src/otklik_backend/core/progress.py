from pydantic import BaseModel


class PullProgress(BaseModel):
    status: str
    completed_bytes: int = 0
    total_bytes: int = 0
    percent: float = 0.0
    done: bool = False
