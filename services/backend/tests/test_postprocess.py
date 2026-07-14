import pytest

from otklik_backend.ai.postprocess import LetterCleaner


@pytest.fixture
def cleaner() -> LetterCleaner:
    return LetterCleaner()


BODY = (
    "Здравствуйте! Меня заинтересовала ваша вакансия: за пять лет в закупках я "
    "выстроил работу с поставщиками и снизил издержки на четверть. Готов принести "
    "этот опыт в вашу команду и обсудить детали на встрече."
)


def test_strips_signature_with_placeholder(cleaner: LetterCleaner) -> None:
    assert cleaner.clean(f"{BODY}\n\nС уважением,\n[Ваше имя]") == BODY


def test_strips_signature_with_meta_parenthesis(cleaner: LetterCleaner) -> None:
    assert cleaner.clean(f"{BODY}\n\nС уважением,\n(текст заканчивается здесь)") == BODY


def test_strips_invented_signature_block(cleaner: LetterCleaner) -> None:
    letter = f"{BODY}\n\nС уважением,\nИван Петров\nМенеджер по продажам"
    assert cleaner.clean(letter) == BODY


def test_strips_english_signature(cleaner: LetterCleaner) -> None:
    assert cleaner.clean(f"{BODY}\n\nBest regards,\nJohn") == BODY


def test_drops_orphaned_salutation(cleaner: LetterCleaner) -> None:
    result = cleaner.clean(f"Уважаемый [Имя],\n\n{BODY}")
    assert "Уважаемый" not in result
    assert result == BODY


def test_removes_placeholders_inline(cleaner: LetterCleaner) -> None:
    result = cleaner.clean(f"{BODY} Свяжитесь со мной: [телефон].")
    assert "[" not in result and "]" not in result
    assert (
        result.endswith("Свяжитесь со мной: .") is False
    )  # пробел перед точкой съеден
    assert "Свяжитесь со мной:." in result


def test_no_brackets_survive(cleaner: LetterCleaner) -> None:
    assert "[" not in cleaner.clean(f"[Company] — {BODY} [Ваше имя]")


def test_idempotent_on_clean_letter(cleaner: LetterCleaner) -> None:
    assert cleaner.clean(BODY) == BODY
    assert cleaner.clean(cleaner.clean(BODY)) == BODY


def test_returns_original_when_cleaning_would_gut_the_letter(
    cleaner: LetterCleaner,
) -> None:
    # Письмо целиком в скобках — чистка съела бы всё. Лучше вернуть как есть,
    # чем отдать пользователю пустоту.
    letter = "С уважением, [Ваше имя]"
    assert cleaner.clean(letter) == letter


def test_keeps_parenthesis_inside_body(cleaner: LetterCleaner) -> None:
    letter = f"Здравствуйте! Я работал в закупках (пять лет) и готов помочь. {BODY}"
    assert "(пять лет)" in cleaner.clean(letter)
