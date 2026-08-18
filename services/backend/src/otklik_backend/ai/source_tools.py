import json
from dataclasses import dataclass

from litellm import ChatCompletionToolParam


@dataclass(frozen=True)
class LLMSource:
    id: int
    label: str
    description: str | None
    url: str
    content: str


class SourceToolProvider:
    def __init__(self, sources: list[LLMSource]) -> None:
        self._sources = sources

    def available_text(self) -> str:
        return "\n".join(
            f"- id={source.id} · {source.label} · {source.description or '—'} · {source.url}"
            for source in self._sources
        )

    def snapshots_text(self) -> str:
        return "\n\n".join(
            f"## {source.label} ({source.url})\n{source.content}"
            for source in self._sources
        )

    def tool_param(self) -> ChatCompletionToolParam:
        return ChatCompletionToolParam(
            type="function",
            function={
                "name": "fetch_source",
                "description": "Return the stored text snapshot for one of the available sources",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_id": {
                            "type": "integer",
                        },
                    },
                    "required": ["source_id"],
                },
            },
        )

    def execute(self, name: str, arguments: str) -> str:
        if name != "fetch_source":
            return f"Unknown tool: {name}"
        try:
            parsed = json.loads(arguments)
            source_id = int(parsed["source_id"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return "Некорректные аргументы вызова fetch_source."
        for source in self._sources:
            if source.id == source_id:
                return source.content
        return "Источник не найден."
