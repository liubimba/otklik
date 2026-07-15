from typing import Any

import litellm
from pydantic import BaseModel

# Только провайдеры с прямой консолью, где пользователь сам генерирует ключ.
# Аггрегаторы (fireworks_ai, together_ai) и инфра-провайдеры (bedrock, azure,
# openrouter, vercel_ai_gateway) исключены: их «получить ключ» — это не поход
# на developers-сайт, а настройка облака. Словарь — единственное место правды.
PROVIDER_KEY_URLS: dict[str, str] = {
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "gemini": "https://aistudio.google.com/apikey",
    "mistral": "https://console.mistral.ai/api-keys",
    "groq": "https://console.groq.com/keys",
    "deepseek": "https://platform.deepseek.com/api_keys",
    "cohere": "https://dashboard.cohere.com/api-keys",
    "xai": "https://console.x.ai",
    "perplexity": "https://www.perplexity.ai/settings/api",
    "gigachat": "https://developers.sber.ru/studio/workspaces",
    "ai21": "https://studio.ai21.com/account/api-key",
}


class CloudModelOption(BaseModel):
    model: str  # LiteLLM-строка, напр. "anthropic/claude-3-5-sonnet"
    label: str  # человекочитаемое имя (часть после "/")
    provider: str  # litellm_provider
    key_url: str  # консоль провайдера из PROVIDER_KEY_URLS


class CloudCatalog:
    """Список облачных чат-моделей, которыми реально можно пользоваться с одним
    вставленным ключом. Источник — каталог LiteLLM, но отфильтрованный до
    провайдеров с прямой консолью: пробное письмо в конце мастера всё равно
    докажет работоспособность, а список не тонет в 2000+ инфра-моделей."""

    def __init__(self, model_cost: dict[str, Any] | None = None) -> None:
        self._model_cost = model_cost if model_cost is not None else litellm.model_cost

    def options(self) -> list[CloudModelOption]:
        seen: set[str] = set()
        result: list[CloudModelOption] = []
        for model, info in self._model_cost.items():
            if not isinstance(info, dict):
                continue
            if info.get("mode") != "chat":
                continue
            provider = info.get("litellm_provider")
            key_url = PROVIDER_KEY_URLS.get(provider) if provider else None
            if provider is None or key_url is None:
                continue
            if model in seen:
                continue
            seen.add(model)
            result.append(
                CloudModelOption(
                    model=model,
                    label=model.split("/", 1)[-1],
                    provider=provider,
                    key_url=key_url,
                )
            )
        result.sort(key=lambda o: (o.provider, o.model))
        return result
