from otklik_backend.ai.deployment import LLMDeployment


def test_is_usable_local_deployment_without_key() -> None:
    """Локальная модель (задан api_base — адрес Ollama) ключа не просит."""
    deployment = LLMDeployment(
        model="ollama_chat/qwen2.5:7b", api_base="http://localhost:11434"
    )
    assert deployment.is_usable() is True


def test_is_usable_cloud_deployment_without_key() -> None:
    """Облачный пресет без ключа — заготовка, а не рабочий deployment."""
    assert LLMDeployment(model="gigachat/GigaChat-2").is_usable() is False


def test_is_usable_cloud_deployment_with_key() -> None:
    assert (
        LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True).is_usable() is True
    )


def test_is_usable_claude_code_deployment_without_key_or_base() -> None:
    """Подписочный Claude: auth в CLI, ни api_base, ни ключа нет."""
    assert LLMDeployment(model="claude-code/sonnet").is_usable() is True


def test_id_is_stable_and_unique_per_instance() -> None:
    """id — опознавательный знак записи, а не производная от полей: он же станет
    именем аккаунта в связке ключей."""
    a = LLMDeployment(model="gigachat/GigaChat-2")
    b = LLMDeployment(model="gigachat/GigaChat-2")
    assert a.id != b.id
    assert a.id == a.id
    assert len(a.id) == 32 and all(c in "0123456789abcdef" for c in a.id)


def test_matches_ignores_the_key_and_the_id() -> None:
    """Ротация ключа не должна плодить дубль: «тот же deployment» — это модель+адрес."""
    a = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True)
    b = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=False)
    assert a.matches(b) is True
    assert a.id != b.id  # разные записи, но одна и та же «точка подключения»


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


def test_has_api_key_is_set_from_api_key_by_the_transitional_shim() -> None:
    """ВРЕМЕННО (пока api_key ещё живёт в БД, до задачи 5): запись,
    прочитанная из БД с непустым api_key, но без has_api_key, всё равно
    должна остаться usable."""
    deployment = LLMDeployment(model="gigachat/GigaChat-2", api_key="secret")
    assert deployment.has_api_key is True
    assert deployment.is_usable() is True
