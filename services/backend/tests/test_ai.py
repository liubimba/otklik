from otklik_backend.ai.layer import AILayer
from otklik_backend.ai.health import AILayerHealthStatus
from otklik_backend.ai.result import AICoverLetterResult
from otklik_backend.ai.exceptions import GenerationCoverLetterError
from otklik_backend.ai.deployment import LLMDeployment, ResolvedDeployment
from otklik_backend.ai.source_tools import LLMSource
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


def _fake_model_response(
    *,
    content: str,
    model: str = "test-model",
    usage: dict[str, int] | None = None,
    response_cost: float | None = None,
) -> ModelResponse:
    response = ModelResponse(
        id="test",
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        model=model,
        usage=usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )
    if response_cost is not None:
        response._hidden_params["response_cost"] = response_cost
    return response


def _fake_tool_call_response(
    *,
    arguments: str,
    call_id: str = "c1",
    name: str = "fetch_source",
    model: str = "test-model",
    usage: dict[str, int] | None = None,
    response_cost: float | None = None,
) -> ModelResponse:
    response = ModelResponse(
        id="test",
        choices=[
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": arguments},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        model=model,
        usage=usage
        or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )
    if response_cost is not None:
        response._hidden_params["response_cost"] = response_cost
    return response


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


async def test_tool_capable_model_runs_fetch_source_loop(
    make_ai_layer, vacancy_model: VacancyAPISchema, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "otklik_backend.ai.layer.supports_function_calling", lambda *a, **k: True
    )
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.side_effect = [
        _fake_tool_call_response(
            arguments='{"source_id": 1}',
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            response_cost=0.001,
        ),
        _fake_model_response(
            content="letter",
            usage={"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
            response_cost=0.002,
        ),
    ]
    sources = [
        LLMSource(id=1, label="GH", description=None, url="u", content="SNAP-CONTENT")
    ]
    result = await layer.generate_cover_letter(
        vacancy_model=vacancy_model, resume="резюме", style="", sources=sources
    )
    assert layer._router.acompletion.await_count == 2
    first_call = layer._router.acompletion.await_args_list[0]
    assert "tools" in first_call.kwargs
    second_call = layer._router.acompletion.await_args_list[1]
    tool_messages = [
        m for m in second_call.kwargs["messages"] if m.get("role") == "tool"
    ]
    assert len(tool_messages) == 1
    assert tool_messages[0]["content"] == "SNAP-CONTENT"
    assert result.text == "letter"
    assert result.prompt_tokens == 17
    assert result.completion_tokens == 8
    assert result.total_tokens == 25
    assert result.cost_usd == pytest.approx(0.003)


async def test_tool_loop_caps_iterations(
    make_ai_layer, vacancy_model: VacancyAPISchema, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "otklik_backend.ai.layer.supports_function_calling", lambda *a, **k: True
    )
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.side_effect = lambda **_: _fake_tool_call_response(
        arguments='{"source_id": 1}'
    )
    sources = [
        LLMSource(id=1, label="GH", description=None, url="u", content="SNAP-CONTENT")
    ]
    result = await layer.generate_cover_letter(
        vacancy_model=vacancy_model, resume="резюме", style="", sources=sources
    )
    assert layer._router.acompletion.await_count == 5
    assert isinstance(result, AICoverLetterResult)


async def test_non_tool_model_injects_snapshots(
    make_ai_layer, vacancy_model: VacancyAPISchema, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "otklik_backend.ai.layer.supports_function_calling", lambda *a, **k: False
    )
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.return_value = _fake_model_response(content="letter")
    sources = [
        LLMSource(id=1, label="GH", description=None, url="u", content="SNAP-CONTENT")
    ]
    await layer.generate_cover_letter(
        vacancy_model=vacancy_model, resume="резюме", style="", sources=sources
    )
    assert layer._router.acompletion.await_count == 1
    call = layer._router.acompletion.await_args_list[0]
    assert "tools" not in call.kwargs
    assert "SNAP-CONTENT" in str(call.kwargs["messages"])


async def test_no_sources_keeps_single_shot(
    make_ai_layer, vacancy_model: VacancyAPISchema
) -> None:
    layer: AILayer = make_ai_layer([_resolved()])
    layer._router.acompletion.return_value = _fake_model_response(content="letter")
    await layer.generate_cover_letter(
        vacancy_model=vacancy_model, resume="резюме", style="", sources=None
    )
    assert layer._router.acompletion.await_count == 1
    call = layer._router.acompletion.await_args_list[0]
    assert "tools" not in call.kwargs
