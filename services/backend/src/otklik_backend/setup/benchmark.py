import asyncio
import time
from collections.abc import Callable
from enum import Enum

from pydantic import BaseModel

from otklik_backend.ai.deployment import ResolvedDeployment
from otklik_backend.ai.error_hints import humanize_llm_error
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
    DEADLINE = "deadline"
    MODEL_ERROR = "model_error"


class BenchmarkResult(BaseModel):
    passed: bool
    seconds: float
    letter: str | None = None
    failure_reason: BenchmarkFailureReason | None = None
    error: str | None = None


class BenchmarkRunner:
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
                error=humanize_llm_error(error),
            )

        elapsed = time.monotonic() - started
        self._log.info("Benchmark: letter written in %.1fs", elapsed)
        return BenchmarkResult(
            passed=True, seconds=round(elapsed, 1), letter=result.text
        )
