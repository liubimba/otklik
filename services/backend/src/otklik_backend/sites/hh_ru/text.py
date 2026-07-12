import re
import unicodedata


# Latin-двойники, которые могут заменять кириллические буквы
# в нашем словаре успешных фраз («Вы откликнулись», «Вас пригласили»).
# Сворачиваем Latin → кириллица, чтобы сравнение было устойчиво.
_LATIN_TO_CYR = str.maketrans(
    {
        "A": "А",
        "a": "а",
        "B": "В",
        "C": "С",
        "c": "с",
        "E": "Е",
        "e": "е",
        "H": "Н",
        "K": "К",
        "k": "к",
        "M": "М",
        "O": "О",
        "o": "о",
        "P": "Р",
        "p": "р",
        "T": "Т",
        "X": "Х",
        "x": "х",
        "y": "у",
    }
)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_LATIN_TO_CYR)
    text = text.replace("\xa0", " ")
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text
