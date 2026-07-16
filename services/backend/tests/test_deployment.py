from otklik_backend.ai.deployment import LLMDeployment


def test_is_usable_local_deployment_without_key() -> None:
    """Локальная модель (задан api_base — адрес Ollama) не просит ключ."""
    deployment = LLMDeployment(
        model="ollama_chat/qwen2.5:7b", api_base="http://localhost:11434"
    )
    assert deployment.is_usable() is True


def test_is_usable_cloud_deployment_without_key() -> None:
    """Облачный пресет с пустым ключом — заготовка, а не рабочий deployment."""
    deployment = LLMDeployment(model="gigachat/GigaChat-2")
    assert deployment.is_usable() is False


def test_is_usable_cloud_deployment_with_key() -> None:
    deployment = LLMDeployment(model="gigachat/GigaChat-2", api_key="secret")
    assert deployment.is_usable() is True


def test_is_usable_claude_code_deployment_without_key_or_base() -> None:
    """Подписочный Claude не имеет ни api_base, ни api_key — auth в CLI.
    Он всё равно рабочий, и мастер должен считать шаг пройденным."""
    deployment = LLMDeployment(model="claude-code/sonnet")
    assert deployment.is_usable() is True
