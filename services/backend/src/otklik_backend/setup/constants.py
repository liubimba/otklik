OLLAMA_HOST = "http://localhost:11434"

LOCAL_MODEL_TAG = "qwen2.5:7b"
LOCAL_MODEL = f"ollama_chat/{LOCAL_MODEL_TAG}"

CLOUD_MODEL = "gigachat/GigaChat-2"

MIN_RAM_GB = 16
MIN_CORES = 8

BENCHMARK_DEADLINE_SEC = 45.0

CLAUDE_CODE_PROVIDER = "claude-code"
CLAUDE_CODE_PREFIX = "claude-code/"
CLAUDE_CODE_DEFAULT_MODEL = "claude-code/sonnet"
CLAUDE_CODE_MODEL_OPTIONS: list[tuple[str, str]] = [
    ("claude-code/sonnet", "Claude Sonnet"),
    ("claude-code/opus", "Claude Opus"),
    ("claude-code/haiku", "Claude Haiku"),
]
