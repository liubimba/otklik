import asyncio
import time
from collections.abc import Callable
from enum import Enum

from pydantic import BaseModel

from otklik_backend.ai.deployment import ResolvedDeployment
from otklik_backend.ai.layer import AILayer
from otklik_backend.ai.result import AICoverLetterResult
from otklik_backend.log import get_logger
from otklik_backend.setup.constants import BENCHMARK_DEADLINE_SEC
from otklik_backend.setup.fixtures import (
    BENCHMARK_RESUME,
    BENCHMARK_STYLE,
    BENCHMARK_VACANCY,
)


class BenchmarkFailureReason(str, Enum):
    """Почему `passed=False` — фронтенду нужно различать, а не только знать факт провала.

    DEADLINE: модель ответила, но не уложилась в дедлайн — «машина медленная»,
    честная развилка (оставаться на локальной / уйти в облако).
    MODEL_ERROR: модель не ответила вовсе (упала, OOM, соединение отвалилось) —
    это не про скорость, показывать «медленно» здесь нельзя: пользователь
    решит остаться на модели, которая ни разу не сработала.
    """

    DEADLINE = "deadline"
    MODEL_ERROR = "model_error"


class BenchmarkResult(BaseModel):
    passed: bool
    seconds: float
    letter: str | None = None
    # None когда passed=True. Иначе — DEADLINE или MODEL_ERROR (см. выше).
    failure_reason: BenchmarkFailureReason | None = None
    # Текст исключения — только при MODEL_ERROR, для диагностики на экране.
    error: str | None = None


class BenchmarkRunner:
    """Пишет одно настоящее письмо с дедлайном и решает, тянет ли машина модель.

    Порог гейта (≤45 с на письмо) и таймаут запроса — одно и то же число: мы
    измеряем ровно то, что пользователь будет чувствовать, и ровно тем
    критерием, которым задан порог. Никаких экстраполяций, которые потом
    пришлось бы защищать.

    Это же и есть проверка готовности перед «Готово» (P0-5): успешный замер
    доказывает, что модель отвечает, — отдельный health-ping не нужен.
    """

    def __init__(
        self,
        deadline_sec: float = BENCHMARK_DEADLINE_SEC,
        layer_factory: Callable[[list[ResolvedDeployment]], AILayer] = AILayer,
    ) -> None:
        self._deadline_sec = deadline_sec
        self._layer_factory = layer_factory
        self._log = get_logger(__name__)

    async def run(
        self, deployment: ResolvedDeployment, deadline_sec: float | None = None
    ) -> BenchmarkResult:
        deadline = deadline_sec if deadline_sec is not None else self._deadline_sec
        # Ровно один deployment: с несколькими LiteLLM-роутер построит
        # кросс-продукт фолбэков и может втихую подменить модель — тогда мы
        # замерим не то, что думаем.
        layer = self._layer_factory([deployment])
        started = time.monotonic()
        try:
            async with asyncio.timeout(deadline):
                result: AICoverLetterResult = await layer.generate_cover_letter(
                    vacancy_model=BENCHMARK_VACANCY,
                    resume=BENCHMARK_RESUME,
                    style=BENCHMARK_STYLE,
                )
        except TimeoutError:
            elapsed = time.monotonic() - started
            self._log.info("Benchmark: model did not finish within %.1fs", deadline)
            return BenchmarkResult(
                passed=False,
                seconds=round(elapsed, 1),
                failure_reason=BenchmarkFailureReason.DEADLINE,
            )
        except Exception as error:
            elapsed = time.monotonic() - started
            self._log.error("Benchmark failed: %s", error)
            return BenchmarkResult(
                passed=False,
                seconds=round(elapsed, 1),
                failure_reason=BenchmarkFailureReason.MODEL_ERROR,
                error=str(error),
            )

        elapsed = time.monotonic() - started
        self._log.info("Benchmark: letter written in %.1fs", elapsed)
        return BenchmarkResult(
            passed=True, seconds=round(elapsed, 1), letter=result.text
        )
