import asyncio

from otklik_backend.ai.deployment import LLMDeployment
from otklik_backend.ai.result import AICoverLetterResult
from otklik_backend.setup.benchmark import BenchmarkFailureReason, BenchmarkRunner

DEPLOYMENT = LLMDeployment(model="ollama_chat/qwen2.5:7b", api_base="http://x:11434")


class _FakeLayer:
    def __init__(self, delay: float, text: str = "письмо") -> None:
        self._delay = delay
        self._text = text
        self.cancelled = False

    async def generate_cover_letter(self, **_: object) -> AICoverLetterResult:
        try:
            await asyncio.sleep(self._delay)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return AICoverLetterResult(
            text=self._text,
            model_used="ollama_chat/qwen2.5:7b",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            was_fallback=False,
            cost_usd=0.0,
        )


async def test_fast_machine_passes_and_returns_the_letter() -> None:
    layer = _FakeLayer(delay=0.01, text="Здравствуйте! Это письмо.")
    runner = BenchmarkRunner(deadline_sec=1.0, layer_factory=lambda _: layer)  # type: ignore[arg-type, return-value]

    result = await runner.run(deployment=DEPLOYMENT)

    assert result.passed is True
    assert result.letter == "Здравствуйте! Это письмо."
    assert result.seconds < 1.0
    assert result.failure_reason is None
    assert result.error is None


async def test_slow_machine_fails_on_the_deadline() -> None:
    """Модель ответила, просто не успела — это DEADLINE, а не ошибка модели.
    Фронтенд обязан отличать эту ветку от MODEL_ERROR (см. test_model_error_...)."""
    layer = _FakeLayer(delay=10.0)
    runner = BenchmarkRunner(deadline_sec=0.05, layer_factory=lambda _: layer)  # type: ignore[arg-type, return-value]

    result = await runner.run(deployment=DEPLOYMENT)

    assert result.passed is False
    assert result.letter is None
    # Не ставим положительный порог на seconds: runner округляет elapsed до
    # одного знака (round(elapsed, 1)), поэтому любое elapsed < 0.05 c схлопывается
    # в 0.0, а на грубом таймере Windows дедлайн в 0.05 c именно так и меряется
    # (проходило на Linux/macOS лишь по удаче тайминга — CI на windows-latest
    # падал на `0.0 >= 0.05`). Смысл ветки — DEADLINE, а не точная длительность;
    # его несёт failure_reason ниже. Здесь достаточно, что время неотрицательно.
    assert result.seconds >= 0.0
    assert result.failure_reason is BenchmarkFailureReason.DEADLINE
    assert result.error is None


async def test_deadline_actually_cancels_the_request() -> None:
    """Иначе брошенная генерация продолжит жечь CPU на слабой машине —
    ровно там, где его и так нет."""
    layer = _FakeLayer(delay=10.0)
    runner = BenchmarkRunner(deadline_sec=0.05, layer_factory=lambda _: layer)  # type: ignore[arg-type, return-value]

    await runner.run(deployment=DEPLOYMENT)

    assert layer.cancelled is True


class _SlowLayer:
    def __init__(self, *_args, **_kwargs) -> None: ...
    async def generate_cover_letter(self, **_kwargs):
        await asyncio.sleep(0.2)
        raise AssertionError("should have hit the deadline first")


async def test_run_honors_per_call_deadline_override():
    runner = BenchmarkRunner(deadline_sec=999, layer_factory=_SlowLayer)
    result = await runner.run(
        deployment=LLMDeployment(model="x", api_base="http://h"),
        deadline_sec=0.05,
    )
    assert result.passed is False
    assert result.failure_reason == BenchmarkFailureReason.DEADLINE


async def test_model_error_fails_the_benchmark() -> None:
    """Модель вообще не ответила (упала, OOM, обрыв соединения) — это
    MODEL_ERROR с текстом причины, а не «машина медленная». Смешивание этих
    двух исходов раньше вело к записи deployment'а на модель, которая ни разу
    не ответила."""

    class _BrokenLayer:
        async def generate_cover_letter(self, **_: object) -> AICoverLetterResult:
            raise RuntimeError("connection refused")

    runner = BenchmarkRunner(deadline_sec=1.0, layer_factory=lambda _: _BrokenLayer())  # type: ignore[arg-type, return-value]

    result = await runner.run(deployment=DEPLOYMENT)

    assert result.passed is False
    assert result.letter is None
    assert result.failure_reason is BenchmarkFailureReason.MODEL_ERROR
    assert result.error == "connection refused"
