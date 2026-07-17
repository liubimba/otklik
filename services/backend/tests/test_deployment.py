from otklik_backend.ai.deployment import LLMDeployment


def test_is_usable_local_deployment_without_key() -> None:
    deployment = LLMDeployment(
        model="ollama_chat/qwen2.5:7b", api_base="http://localhost:11434"
    )
    assert deployment.is_usable() is True


def test_is_usable_cloud_deployment_without_key() -> None:
    assert LLMDeployment(model="gigachat/GigaChat-2").is_usable() is False


def test_is_usable_cloud_deployment_with_key() -> None:
    assert (
        LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True).is_usable() is True
    )


def test_is_usable_claude_code_deployment_without_key_or_base() -> None:
    assert LLMDeployment(model="claude-code/sonnet").is_usable() is True


def test_id_is_stable_and_unique_per_instance() -> None:
    a = LLMDeployment(model="gigachat/GigaChat-2")
    b = LLMDeployment(model="gigachat/GigaChat-2")
    assert a.id != b.id
    assert a.id == a.id
    assert len(a.id) == 32 and all(c in "0123456789abcdef" for c in a.id)


def test_matches_ignores_the_key_and_the_id() -> None:
    a = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True)
    b = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=False)
    assert a.matches(b) is True
    assert a.id != b.id


def test_matches_distinguishes_model_and_base() -> None:
    base = LLMDeployment(model="ollama_chat/qwen2.5:7b", api_base="http://a")
    assert (
        base.matches(LLMDeployment(model="ollama_chat/qwen2.5:7b", api_base="http://b"))
        is False
    )
    assert (
        base.matches(LLMDeployment(model="ollama_chat/other", api_base="http://a"))
        is False
    )


def test_deployment_model_cannot_carry_a_secret() -> None:
    deployment = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True)
    assert "api_key" not in deployment.model_dump(mode="json")
    assert not hasattr(deployment, "api_key")

    sneaky = LLMDeployment(
        model="gigachat/GigaChat-2", has_api_key=True, api_key="sk-should-vanish"
    )  # type: ignore[call-arg]
    assert '"api_key"' not in sneaky.model_dump_json()
    assert "sk-should-vanish" not in sneaky.model_dump_json()
