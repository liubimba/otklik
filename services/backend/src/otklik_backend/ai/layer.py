from collections.abc import AsyncIterator, Sequence
from typing import cast

from otklik_backend.ai.claude_code import register_claude_code_provider
from otklik_backend.ai.deployment import LLMDeployment
from otklik_backend.ai.postprocess import LetterCleaner
from litellm import (
    AllMessageValues,
    CustomStreamWrapper,
    DeploymentTypedDict,
    LiteLLMParamsTypedDict,
    ModelResponse,
)
from litellm.router import Router
from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.ai.result import AICoverLetterResult
from otklik_backend.ai.prompts import PromptBuilder
from otklik_backend.ai.exceptions import GenerationCoverLetterError
from otklik_backend.ai.health import AILayerHealthStatus
from otklik_backend.log import get_logger


class AILayer:
    def __init__(self, deployments: list[LLMDeployment] = []) -> None:
        # Регистрируем провайдер claude-code, чтобы Router умел маршрутизировать
        # model='claude-code/...' в CLI `claude -p`. Идемпотентно.
        register_claude_code_provider()
        self._prompt_builder = PromptBuilder()
        self._cleaner = LetterCleaner()
        self._log = get_logger(__name__)
        self.rebuild(deployments=deployments)

    async def generate_cover_letter(
        self,
        vacancy_model: VacancyAPISchema,
        resume: str,
        style: str,
        system_prompt: str | None = None,
    ) -> AICoverLetterResult:
        self._log.info(
            "Generating cover letter with vacancy_model: %s, resume length: %d, style: %s",
            vacancy_model,
            len(resume),
            style,
        )
        # Раньше здесь был health-ping — отдельный полный вызов модели перед
        # каждой генерацией (по результатам замера моделей — отчёт вне
        # репозитория: +59с на локальной модели, и это ещё не считая второго
        # пинга из вызывающего сервиса). Мёртвая модель роняет acompletion
        # ниже и превращается в GenerationCoverLetterError — ping не добавлял
        # информации, только цену.
        if len(self._deployments) == 0:
            self._log.error(
                "Failed to generate cover letter: no deployments configured"
            )
            raise GenerationCoverLetterError("no deployments configured")
        try:
            llm: LLMDeployment = self._get_primary_llm()
            messages: list[AllMessageValues] = (
                self._prompt_builder.build_cover_letter_prompt(
                    vacancy_model=vacancy_model,
                    resume=resume,
                    style=style,
                    system_prompt=system_prompt,
                )
            )
            self._log.info(
                "Sending request to AI model: %s with messages: %s", llm.model, messages
            )
            response: ModelResponse = await self._router.acompletion(
                model=llm.model, messages=messages
            )
            self._log.info(
                "Received response from AI model: %s with content: %s",
                response.model,
                response.choices[0].message.content,
            )
            return AICoverLetterResult(
                text=self._cleaner.clean(response.choices[0].message.content or ""),
                model_used=response.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                was_fallback=response._hidden_params.get("model_id", llm.id())
                != llm.id(),
                cost_usd=response._hidden_params.get("response_cost", 0.0),
            )
        except Exception as e:
            self._log.error("Failed to generate cover letter: %s", str(e))
            raise GenerationCoverLetterError(detail=str(e))

    async def stream_letter_chat(
        self,
        vacancy_model: VacancyAPISchema,
        resume: str,
        style: str,
        current_letter: str,
        history: Sequence[tuple[str, str]],
        user_message: str,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a conversational letter-editing turn token-by-token.

        The model replies with a JSON object `{reply, letter}` (JSON mode), so
        the caller parses the stream into the reply and the (optional) revised
        letter without depending on a fragile in-band text marker.
        """
        # Та же логика, что в generate_cover_letter — бесплатная проверка вместо
        # платного health-ping'а.
        if len(self._deployments) == 0:
            self._log.error("Cannot start letter chat: no deployments configured")
            raise GenerationCoverLetterError("no deployments configured")

        llm: LLMDeployment = self._get_primary_llm()
        messages: list[AllMessageValues] = (
            self._prompt_builder.build_letter_chat_messages(
                vacancy_model=vacancy_model,
                resume=resume,
                style=style,
                current_letter=current_letter,
                history=history,
                user_message=user_message,
                system_prompt=system_prompt,
            )
        )
        # NB: no `response_format=json_object` — on some providers (Groq) that
        # buffers the whole completion and kills token-by-token streaming. The
        # prompt asks for a bare JSON object and StreamingJsonChatParser is
        # tolerant (anchors on the field keys, skips any fences), so we keep the
        # live stream and still parse structurally.
        stream: CustomStreamWrapper = cast(
            CustomStreamWrapper,
            await self._router.acompletion(
                model=llm.model, messages=messages, stream=True
            ),
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def get_health_status(self) -> AILayerHealthStatus:
        self._log.info("Check health status...")
        if len(self._deployments) == 0:
            self._log.warn("Layer has no deployments")
            return AILayerHealthStatus.NO_DEPLOYMENTS
        try:
            await self._router.acompletion(
                model=self._get_primary_llm().model,
                messages=self._prompt_builder.build_ping(),
            )
        except Exception as e:
            self._log.error("Health check failed with error", error=str(e))
            return AILayerHealthStatus.UNHEALTHY
        self._log.info("Layer is healthy")
        return AILayerHealthStatus.HEALTHY

    def rebuild(self, deployments: list[LLMDeployment]) -> None:
        self._deployments = deployments
        self._router = Router(
            model_list=self._generate_model_list(deployments=deployments),
            fallbacks=self._generate_fallbacks(deployments=deployments),
        )

    def _get_primary_llm(self) -> LLMDeployment:
        return self._deployments[0]

    def _map_llm_to_deploy(self, llm: LLMDeployment) -> DeploymentTypedDict:
        return DeploymentTypedDict(
            model_name=llm.model,
            model_info={"id": llm.id()},
            litellm_params=LiteLLMParamsTypedDict(
                model=llm.model, api_base=llm.api_base, api_key=llm.api_key
            ),
        )

    def _generate_model_list(
        self, deployments: list[LLMDeployment]
    ) -> list[DeploymentTypedDict]:
        return list(map(lambda llm: self._map_llm_to_deploy(llm=llm), deployments))

    def _generate_fallbacks(
        self, deployments: list[LLMDeployment]
    ) -> list[dict[str, list[str]]]:
        unique_models: list[str] = list(
            dict.fromkeys(deploy.model for deploy in deployments)
        )
        return [
            {model: [other for other in unique_models if other != model]}
            for model in unique_models
        ]
