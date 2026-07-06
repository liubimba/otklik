from headhunter_backend.orchestrator.letter_chat_service import (
    StreamingJsonChatParser,
)


def _run(chunks: list[str]) -> StreamingJsonChatParser:
    parser = StreamingJsonChatParser()
    for chunk in chunks:
        parser.feed(chunk)
    parser.finish()
    return parser


def _chunked(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def test_reply_and_letter_are_separated() -> None:
    payload = '{"reply": "Сделал формальнее.", "letter": "Уважаемый работодатель!"}'
    p = _run(_chunked(payload, 4))
    assert p.reply == "Сделал формальнее."
    assert p.has_letter is True
    assert p.letter == "Уважаемый работодатель!"


def test_letter_never_leaks_into_reply() -> None:
    # The exact failure mode of the old delimiter approach: a whole letter in
    # the response must not end up in the reply channel.
    letter = "Полностью переписанное письмо с деталями."
    payload = f'{{"reply": "Готово.", "letter": "{letter}"}}'
    p = _run(_chunked(payload, 3))
    assert letter not in p.reply
    assert p.letter == letter


def test_question_has_null_letter() -> None:
    payload = (
        '{"reply": "Тон формальный, потому что вакансия деловая.", "letter": null}'
    )
    p = _run(_chunked(payload, 6))
    assert p.reply.startswith("Тон формальный")
    assert p.has_letter is False
    assert p.letter == ""


def test_json_escapes_are_decoded() -> None:
    # \n -> newline, \" -> quote inside the letter body.
    payload = '{"reply": "ok", "letter": "Строка один\\nСтрока \\"два\\""}'
    p = _run(_chunked(payload, 2))
    assert p.letter == 'Строка один\nСтрока "два"'


def test_escape_split_across_chunk_boundary_is_not_half_emitted() -> None:
    payload = '{"reply": "ok", "letter": "a\\nb"}'
    # Force the backslash and the "n" into separate feeds.
    parser = StreamingJsonChatParser()
    emitted: list[tuple[str, str]] = []
    boundary = payload.index("\\n")
    for chunk in [payload[: boundary + 1], payload[boundary + 1 :]]:
        emitted += parser.feed(chunk)
    parser.finish()
    letter = "".join(t for c, t in emitted if c == "letter")
    assert letter == "a\nb"
    assert "\\" not in letter


def test_streaming_one_char_at_a_time() -> None:
    payload = '{"reply": "hi", "letter": "body text"}'
    p = _run(list(payload))
    assert p.reply == "hi"
    assert p.letter == "body text"


def test_reply_deltas_stream_before_letter_deltas() -> None:
    payload = '{"reply": "abc", "letter": "xyz"}'
    parser = StreamingJsonChatParser()
    channels: list[str] = []
    for ch in payload:
        for channel, _ in parser.feed(ch):
            channels.append(channel)
    # every reply delta comes before any letter delta
    assert "reply" in channels and "letter" in channels
    assert channels.index("letter") > channels.index("reply")
    last_reply = len(channels) - 1 - channels[::-1].index("reply")
    first_letter = channels.index("letter")
    assert last_reply < first_letter
