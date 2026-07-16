import json
from unittest.mock import patch

from otklik_backend.ai.deployment import LLMDeployment
from otklik_backend.ai.layer import AILayer
from otklik_backend.ai.result import AICoverLetterResult
from otklik_backend.api.schemas import (
    EmploymentType,
    VacancyAPISchema,
    WorkFormat,
)


class _FakeProc:
    def __init__(self, stdout: bytes):
        self._stdout = stdout
        self.returncode = 0

    async def communicate(self, _input: bytes | None = None):
        return self._stdout, b""

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode


def _vacancy() -> VacancyAPISchema:
    return VacancyAPISchema(
        title="Python Developer",
        apply_link="https://hh.ru/vacancy/1",
        description="Build backend services.",
        company_name="ACME",
        salary=None,
        work_formats=[WorkFormat.REMOTE],
        employment_types=[EmploymentType.FULL_TIME],
        work_experience="1-3 years",
    )


async def test_ailayer_routes_claude_deployment_through_adapter() -> None:
    """Полный путь: AILayer с реальным Router (не мок) и claude-code-моделью
    должен уйти в ClaudeCodeLLM, а тот — в поддельный `claude -p`."""
    layer = AILayer(deployments=[LLMDeployment(model="claude-code/sonnet")])
    proc = _FakeProc(
        json.dumps(
            {
                "result": "Здравствуйте! Меня заинтересовала ваша вакансия.",
                "model": "claude-sonnet",
                "usage": {"input_tokens": 10, "output_tokens": 20},
                "total_cost_usd": 0.03,
            }
        ).encode()
    )

    async def _fake_exec(*args, **kwargs):
        return proc

    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        patch(
            "otklik_backend.ai.claude_code.asyncio.create_subprocess_exec",
            side_effect=_fake_exec,
        ),
    ):
        result = await layer.generate_cover_letter(
            vacancy_model=_vacancy(), resume="резюме", style="деловой"
        )

    assert isinstance(result, AICoverLetterResult)
    assert result.text == "Здравствуйте! Меня заинтересовала ваша вакансия."
    assert result.completion_tokens == 20


async def test_claude_deployment_receives_model_alias_without_prefix() -> None:
    """`claude -p --model` должен получить `sonnet`, а не `claude-code/sonnet`."""
    layer = AILayer(deployments=[LLMDeployment(model="claude-code/opus")])
    captured: dict[str, list[str]] = {}

    class _CapturingProc(_FakeProc):
        pass

    async def _fake_exec(*args, **kwargs):
        captured["args"] = list(args)
        return _FakeProc(json.dumps({"result": "ok", "usage": {}}).encode())

    with (
        patch(
            "otklik_backend.ai.claude_code.resolve_claude_binary",
            return_value="/usr/bin/claude",
        ),
        patch(
            "otklik_backend.ai.claude_code.asyncio.create_subprocess_exec",
            side_effect=_fake_exec,
        ),
    ):
        await layer.generate_cover_letter(
            vacancy_model=_vacancy(), resume="r", style=""
        )

    assert "--model" in captured["args"]
    assert captured["args"][captured["args"].index("--model") + 1] == "opus"
    assert "--bare" not in captured["args"]
    assert "--permission-mode" in captured["args"]
