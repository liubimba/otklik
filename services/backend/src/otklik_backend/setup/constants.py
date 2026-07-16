"""Единственное место, где записаны решения гейта.

Числа не выдуманы: по результатам замера моделей (отчёт вне репозитория —
каталог `docs/` не в гите). Менять — только пересняв замер.
"""

OLLAMA_HOST = "http://localhost:11434"

# Тег так, как его знает Ollama (для /api/tags и /api/pull).
LOCAL_MODEL_TAG = "qwen2.5:7b"
# Строка так, как её знает LiteLLM. Именно `ollama_chat/`, а не `ollama/`:
# с последним LiteLLM схлопывает system-роль в общий текст, и промпт, на
# котором держится всё качество, частично теряется.
LOCAL_MODEL = f"ollama_chat/{LOCAL_MODEL_TAG}"

# Ветка слабого железа. `GigaChat-2-Lite` не существует — API отдаёт 404.
CLOUD_MODEL = "gigachat/GigaChat-2"

# Пре-фильтр: ниже этого локальную модель даже не качаем. GPU не проверяем —
# машина с дискретной картой почти всегда проходит порог по RAM, а точный
# вердикт всё равно выносит замер.
MIN_RAM_GB = 16
MIN_CORES = 8

# Порог гейта и таймаут замера — одно и то же число.
BENCHMARK_DEADLINE_SEC = 45.0

# Провайдер Claude Code: генерация через локально установленный `claude -p` на
# подписке пользователя. Дискриминатор — префикс модели, отдельного поля в
# LLMDeployment не заводим.
CLAUDE_CODE_PROVIDER = "claude-code"
CLAUDE_CODE_PREFIX = "claude-code/"
CLAUDE_CODE_DEFAULT_MODEL = "claude-code/sonnet"
# (строка модели для LiteLLM, подпись для UI). Алиасы (`sonnet`/`opus`/`haiku`)
# понимает `claude -p --model`.
CLAUDE_CODE_MODEL_OPTIONS: list[tuple[str, str]] = [
    ("claude-code/sonnet", "Claude Sonnet"),
    ("claude-code/opus", "Claude Opus"),
    ("claude-code/haiku", "Claude Haiku"),
]
