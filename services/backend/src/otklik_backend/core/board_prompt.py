from dataclasses import dataclass
from enum import Enum


class BoardPromptMode(str, Enum):
    APPEND = "append"
    REPLACE = "replace"


@dataclass(frozen=True)
class BoardPrompt:
    mode: BoardPromptMode
    text: str

    @classmethod
    def from_stored(cls, raw: dict[str, str] | None) -> "BoardPrompt | None":
        if not raw:
            return None
        text = (raw.get("text") or "").strip()
        if not text:
            return None
        mode = raw.get("mode", BoardPromptMode.APPEND.value)
        try:
            parsed = BoardPromptMode(mode)
        except ValueError:
            parsed = BoardPromptMode.APPEND
        return cls(mode=parsed, text=text)

    def to_stored(self) -> dict[str, str]:
        return {"mode": self.mode.value, "text": self.text}
