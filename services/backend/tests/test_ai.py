from otklik_backend.ai.layer import AILayer
from otklik_backend.ai.health import AILayerHealthStatus
from otklik_backend.ai.result import AICoverLetterResult
from otklik_backend.ai.exceptions import GenerationCoverLetterError
from otklik_backend.ai.deployment import LLMDeployment, ResolvedDeployment
from otklik_backend.api.schemas import VacancyAPISchema
from litellm import ModelResponse
from pydantic import SecretStr
import pytest


def _resolved(
    model: str = "groq/llama-3.3-70b-versatile", key: str | None = "test-key"
) -> ResolvedDeployment:
    return ResolvedDeployment(
        deployment=LLMDeployment(model=model, has_api_key=key is not None),
        api_key=SecretStr(key) if key else None,
    )


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
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.return_value = _fake_model_response(content="pong")
    assert await layer.get_health_status() == AILayerHealthStatus.HEALTHY
    layer._router.acompletion.assert_awaited_once()


async def test_ai_health_status_no_deployments(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer()
    assert await layer.get_health_status() == AILayerHealthStatus.NO_DEPLOYMENTS


async def test_ai_health_unhealthy(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.side_effect = Exception("Failed to connect to AI model")
    assert await layer.get_health_status() == AILayerHealthStatus.UNHEALTHY
    layer._router.acompletion.assert_awaited_once()


async def test_ai_generate_cover_letter_no_deployments(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer()
    with pytest.raises(GenerationCoverLetterError, match="no deployments configured"):
        await layer.generate_cover_letter(
            vacancy_model=vacancy_model, resume="", style=""
        )


async def test_ai_generate_cover_letter(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer([_resolved()])
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
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.side_effect = Exception("model exploded")
    with pytest.raises(GenerationCoverLetterError, match="model exploded"):
        await layer.generate_cover_letter(
            vacancy_model=vacancy_model, resume="", style=""
        )
    layer._router.acompletion.assert_awaited_once()


async def test_ai_generate_geo_block_error_points_to_the_proxy_setting(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.side_effect = Exception(
        'GroqException - {"message":"Forbidden"}'
    )
    with pytest.raises(GenerationCoverLetterError, match="регион"):
        await layer.generate_cover_letter(
            vacancy_model=vacancy_model, resume="", style=""
        )


async def test_generate_cover_letter_makes_a_single_model_call(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.return_value = _fake_model_response(
        content="Здравствуйте! " + "Меня заинтересовала ваша вакансия. " * 5
    )
    await layer.generate_cover_letter(
        vacancy_model=vacancy_model, resume="резюме", style="деловой"
    )
    assert layer._router.acompletion.await_count == 1


async def test_generate_cover_letter_cleans_the_signature(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer([_resolved()])
    body = (
        "Здравствуйте! Меня заинтересовала ваша вакансия: за пять лет в закупках "
        "я выстроил работу с поставщиками и снизил издержки на четверть. Готов "
        "обсудить детали на встрече."
    )
    layer._router.acompletion.return_value = _fake_model_response(
        content=f"{body}\n\nС уважением,\n[Ваше имя]"
    )
    result: AICoverLetterResult = await layer.generate_cover_letter(
        vacancy_model=vacancy_model, resume="резюме", style="деловой"
    )
    assert result.text == body


async def test_ai_rebuild_swaps_deployments_and_router(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer(
        [_resolved(model="groq/llama-3.3-70b-versatile", key="x")]
    )
    old_router = layer._router
    layer.rebuild(deployments=[_resolved(model="openai/gpt-4o", key="y")])
    assert layer._deployments[0].deployment.model == "openai/gpt-4o"
    assert layer._router is not old_router


def test_ai_layer_disables_ssl_verify_for_gigachat(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer([])
    deploy = layer._map_llm_to_deploy(_resolved(model="gigachat/GigaChat-2-Lite"))
    assert deploy["litellm_params"].get("ssl_verify") is False


def test_ai_layer_keeps_ssl_verify_for_other_providers(make_ai_layer) -> None:
    layer: AILayer = make_ai_layer([])
    deploy = layer._map_llm_to_deploy(_resolved(model="groq/llama-3.3-70b-versatile"))
    assert "ssl_verify" not in deploy["litellm_params"]
