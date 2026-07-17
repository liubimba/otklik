from otklik_backend.setup.cloud_catalog import CloudCatalog, PROVIDER_KEY_URLS

_FAKE_MODEL_COST = {
    "anthropic/claude-3-5-sonnet": {"litellm_provider": "anthropic", "mode": "chat"},
    "openai/gpt-4o": {"litellm_provider": "openai", "mode": "chat"},
    "openai/whisper-1": {"litellm_provider": "openai", "mode": "audio_transcription"},
    "bedrock/anthropic.claude-v2": {"litellm_provider": "bedrock", "mode": "chat"},
    "openai/text-embedding-3-small": {
        "litellm_provider": "openai",
        "mode": "embedding",
    },
}


def _catalog() -> CloudCatalog:
    return CloudCatalog(model_cost=_FAKE_MODEL_COST)


def test_keeps_only_chat_models():
    models = {o.model for o in _catalog().options()}
    assert "openai/whisper-1" not in models
    assert "openai/text-embedding-3-small" not in models
    assert "openai/gpt-4o" in models


def test_drops_providers_without_a_key_console():
    providers = {o.provider for o in _catalog().options()}
    assert "bedrock" not in providers
    assert "anthropic" in providers


def test_attaches_the_provider_key_url():
    option = next(o for o in _catalog().options() if o.model == "openai/gpt-4o")
    assert option.key_url == PROVIDER_KEY_URLS["openai"]
    assert option.label == "gpt-4o"


def test_options_are_sorted_by_provider_then_model():
    options = _catalog().options()
    keys = [(o.provider, o.model) for o in options]
    assert keys == sorted(keys)


def test_real_catalog_is_non_empty_and_all_have_urls():
    options = CloudCatalog().options()
    assert len(options) > 50
    assert all(o.key_url for o in options)
