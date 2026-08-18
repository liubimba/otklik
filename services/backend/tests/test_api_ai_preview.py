from fastapi.testclient import TestClient

from otklik_backend.ai.result import AICoverLetterResult
from otklik_backend.ai.source_tools import LLMSource
from otklik_backend.api.app import app
from otklik_backend.api.dependencies import get_ai_layer, get_context_source_service


class RecordingAILayer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate_cover_letter(
        self,
        vacancy_model,
        resume,
        style,
        system_prompt=None,
        sources=None,
    ) -> AICoverLetterResult:
        self.calls.append(
            {
                "vacancy_model": vacancy_model,
                "resume": resume,
                "style": style,
                "system_prompt": system_prompt,
                "sources": sources,
            }
        )
        return AICoverLetterResult(
            text="PREVIEW LETTER",
            model_used="fake-model",
            prompt_tokens=1,
            completion_tokens=2,
            total_tokens=3,
            was_fallback=False,
            cost_usd=0.0,
        )


class FakeSourcesForLLM:
    def __init__(self, sources: list[LLMSource]) -> None:
        self._sources = sources

    async def list_ok_for_llm(self) -> list[LLMSource]:
        return self._sources


def _body(**overrides) -> dict:
    body = {
        "title": "Senior Python Engineer",
        "description": "Build LLM tooling with FastAPI and Playwright.",
        "company_name": "Otklik",
        "salary": "300000",
    }
    body.update(overrides)
    return body


async def test_preview_returns_generated_letter(client: TestClient) -> None:
    recorder = RecordingAILayer()
    app.dependency_overrides[get_ai_layer] = lambda: recorder
    app.dependency_overrides[get_context_source_service] = lambda: FakeSourcesForLLM([])
    try:
        response = client.post("/api/v1/ai/preview_cover_letter", json=_body())
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["text"] == "PREVIEW LETTER"
        assert payload["model_used"] == "fake-model"
        assert payload["total_tokens"] == 3
        assert recorder.calls[0]["vacancy_model"].title == "Senior Python Engineer"
        assert (
            recorder.calls[0]["vacancy_model"].description
            == "Build LLM tooling with FastAPI and Playwright."
        )
    finally:
        app.dependency_overrides.pop(get_ai_layer, None)
        app.dependency_overrides.pop(get_context_source_service, None)


async def test_preview_passes_ok_sources_to_generation(client: TestClient) -> None:
    recorder = RecordingAILayer()
    sources = [
        LLMSource(id=1, label="GH", description=None, url="u1", content="c1"),
        LLMSource(id=2, label="Habr", description=None, url="u2", content="c2"),
    ]
    app.dependency_overrides[get_ai_layer] = lambda: recorder
    app.dependency_overrides[get_context_source_service] = lambda: FakeSourcesForLLM(
        sources
    )
    try:
        response = client.post("/api/v1/ai/preview_cover_letter", json=_body())
        assert response.status_code == 200, response.text
        assert recorder.calls[0]["sources"] == sources
    finally:
        app.dependency_overrides.pop(get_ai_layer, None)
        app.dependency_overrides.pop(get_context_source_service, None)


async def test_preview_requires_title_and_description(client: TestClient) -> None:
    app.dependency_overrides[get_ai_layer] = lambda: RecordingAILayer()
    app.dependency_overrides[get_context_source_service] = lambda: FakeSourcesForLLM([])
    try:
        missing_title = client.post(
            "/api/v1/ai/preview_cover_letter",
            json={"description": "d"},
        )
        assert missing_title.status_code == 422
        missing_description = client.post(
            "/api/v1/ai/preview_cover_letter",
            json={"title": "t"},
        )
        assert missing_description.status_code == 422
    finally:
        app.dependency_overrides.pop(get_ai_layer, None)
        app.dependency_overrides.pop(get_context_source_service, None)
