from headhunter_backend.ai.layer import AILayer
from headhunter_backend.ai.health import AILayerHealthStatus
from headhunter_backend.ai.result import AICoverLetterResult
from headhunter_backend.ai.exceptions import GenerationCoverLetterException
from headhunter_backend.ai.deployment import LLMDeployment
from headhunter_backend.api.schemas import VacancyAPISchema
from litellm import ModelResponse
import pytest


def _fake_model_response(*, content: str, model: str = "test-model") -> ModelResponse:
    return ModelResponse(
        id="test",
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        model=model,
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )


async def test_ai_health_healthy(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer(
        [LLMDeployment(model="groq/llama-3.3-70b-versatile", api_key="test-key")]
    )
    layer._router.acompletion.return_value = _fake_model_response(content="pong")
    assert await layer.get_health_status() == AILayerHealthStatus.HEALTHY
    layer._router.acompletion.assert_awaited_once()


async def test_ai_health_status_no_deployments(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer()
    assert await layer.get_health_status() == AILayerHealthStatus.NO_DEPLOYMENTS


async def test_ai_health_unhealthy(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer(
        [LLMDeployment(model="groq/llama-3.3-70b-versatile", api_key="test-key")]
    )
    layer._router.acompletion.side_effect = Exception("Failed to connect to AI model")
    assert await layer.get_health_status() == AILayerHealthStatus.UNHEALTHY
    layer._router.acompletion.assert_awaited_once()


async def test_ai_generate_cover_letter_no_deployments(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer()
    with pytest.raises(
        GenerationCoverLetterException, match="no deployments configured"
    ):
        await layer.generate_cover_letter(
            vacancy_model=vacancy_model, resume="", style=""
        )


async def test_ai_generate_cover_letter(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer(
        [LLMDeployment(model="groq/llama-3.3-70b-versatile", api_key="test-key")]
    )
    layer._router.acompletion.return_value = _fake_model_response(content="pong")
    result = await layer.generate_cover_letter(
        vacancy_model=vacancy_model, resume="", style=""
    )
    assert isinstance(result, AICoverLetterResult)
    assert result.text == "pong"
    assert result.model_used == "test-model"


async def test_ai_generate_raises_when_router_fails(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer(
        [LLMDeployment(model="groq/llama-3.3-70b-versatile", api_key="test-key")]
    )
    layer._router.acompletion.return_value = _fake_model_response(
        content="pong"
    )  # ping ok
    layer._router.acompletion.side_effect = [
        _fake_model_response(content="pong"),  # health ping
        Exception("boom"),  # actual generation call
    ]
    with pytest.raises(GenerationCoverLetterException, match="boom"):
        await layer.generate_cover_letter(
            vacancy_model=vacancy_model, resume="", style=""
        )


async def test_ai_rebuild_swaps_deployments_and_router(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer(
        [LLMDeployment(model="groq/llama-3.3-70b-versatile", api_key="x")]
    )
    old_router = layer._router
    layer.rebuild(deployments=[LLMDeployment(model="openai/gpt-4o", api_key="y")])
    assert layer._deployments[0].model == "openai/gpt-4o"
    assert layer._router is not old_router
