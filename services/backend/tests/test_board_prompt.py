from otklik_backend.ai.prompts import (
    DEFAULT_COVER_LETTER_SYSTEM_PROMPT,
    compose_board_system_prompt,
)
from otklik_backend.core.board_prompt import BoardPrompt, BoardPromptMode


def test_no_board_prompt_keeps_the_base_untouched() -> None:
    assert compose_board_system_prompt("base", None) == "base"
    assert compose_board_system_prompt(None, None) is None


def test_replace_mode_uses_only_the_board_text() -> None:
    prompt = BoardPrompt(mode=BoardPromptMode.REPLACE, text="Отклик на проект")
    assert compose_board_system_prompt("base", prompt) == "Отклик на проект"
    assert compose_board_system_prompt(None, prompt) == "Отклик на проект"


def test_append_mode_extends_the_configured_base() -> None:
    prompt = BoardPrompt(mode=BoardPromptMode.APPEND, text="Короче обычного")
    assert compose_board_system_prompt("base", prompt) == "base\n\nКороче обычного"


def test_append_mode_falls_back_to_the_default_when_base_is_absent() -> None:
    prompt = BoardPrompt(mode=BoardPromptMode.APPEND, text="Короче обычного")
    result = compose_board_system_prompt(None, prompt)
    assert result == f"{DEFAULT_COVER_LETTER_SYSTEM_PROMPT}\n\nКороче обычного"


def test_from_stored_ignores_blank_and_unknown_entries() -> None:
    assert BoardPrompt.from_stored(None) is None
    assert BoardPrompt.from_stored({}) is None
    assert BoardPrompt.from_stored({"mode": "replace", "text": "   "}) is None
    fixed = BoardPrompt.from_stored({"mode": "bogus", "text": "hi"})
    assert fixed == BoardPrompt(mode=BoardPromptMode.APPEND, text="hi")


def test_from_stored_round_trips_a_real_entry() -> None:
    prompt = BoardPrompt(mode=BoardPromptMode.REPLACE, text="Отклик")
    assert BoardPrompt.from_stored(prompt.to_stored()) == prompt
