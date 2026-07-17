import re

from otklik_backend.log import get_logger

MIN_LETTER_CHARS = 120


class LetterCleaner:
    _SIGNATURE_TAIL = re.compile(
        r"\n\s*(С уважением|С наилучшими пожеланиями|С наилучшими|Best regards|Sincerely)"
        r"[\s\S]*$",
        re.IGNORECASE,
    )
    _PLACEHOLDER = re.compile(r"\[[^\]\n]*\]")
    _ORPHANED_SALUTATION = re.compile(
        r"^\s*(уважаем\w+|здравствуйте|дорог\w+)[\s,!.:—-]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    _SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.!?;:])")
    _DOUBLE_SPACE = re.compile(r"[ \t]{2,}")
    _EXTRA_NEWLINES = re.compile(r"\n{3,}")

    def __init__(self) -> None:
        self._log = get_logger(__name__)

    def clean(self, text: str) -> str:
        cleaned = self._SIGNATURE_TAIL.sub("", text)
        cleaned = self._PLACEHOLDER.sub("", cleaned)
        cleaned = self._ORPHANED_SALUTATION.sub("", cleaned)
        cleaned = self._SPACE_BEFORE_PUNCT.sub(r"\1", cleaned)
        cleaned = self._DOUBLE_SPACE.sub(" ", cleaned)
        cleaned = self._EXTRA_NEWLINES.sub("\n\n", cleaned)
        cleaned = cleaned.strip()

        if len(cleaned) < MIN_LETTER_CHARS:
            self._log.warning(
                "Letter cleanup would gut the text (%d chars left) — keeping the original",
                len(cleaned),
            )
            return text
        return cleaned
