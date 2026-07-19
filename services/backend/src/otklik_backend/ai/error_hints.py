_REGION_HINT = (
    "Провайдер недоступен из вашего региона (403 Forbidden). "
    "Укажите прокси в Настройках → ИИ или включите VPN."
)

_CONNECTION_HINT = (
    "Не удалось подключиться к провайдеру. "
    "Проверьте адрес прокси в Настройках → ИИ и что VPN включён."
)

_GIGACHAT_AUTH_HINT = (
    "GigaChat не принял ключ. Нужен «Ключ авторизации» из кабинета "
    "(Настройки API → длинная строка без точек), а не access-токен. "
    "И проверьте область (Personal/Corporate)."
)


def humanize_llm_error(error: object) -> str:
    text = str(error)
    lowered = text.lower()
    if "gigachat" in lowered and (
        "can't decode" in lowered
        or "authentication failed" in lowered
        or "authorization" in lowered
    ):
        return _GIGACHAT_AUTH_HINT
    if "forbidden" in lowered or "403" in lowered:
        return _REGION_HINT
    if (
        "all connection attempts failed" in lowered
        or "connection refused" in lowered
        or "connecterror" in lowered
        or "connect error" in lowered
        or "proxy" in lowered
    ):
        return _CONNECTION_HINT
    return text
