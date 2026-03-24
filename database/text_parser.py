# database/text_parser.py — парсинг суммы и описания из распознанного текста
import re
import logging
import natasha

logger = logging.getLogger(__name__)

_SLANG_MAP = {
    "двадцатку": "двадцать рублей",
    "двадцатка": "двадцать рублей",
    "сотку": "сто рублей",
    "сотка": "сто рублей",
    "пятихатку": "пятьсот рублей",
    "пятихатка": "пятьсот рублей",
    "тыщщу": "тысячу рублей",
    "тыщ": "тысячу рублей",
    "двушку": "двести рублей",
    "трёшку": "триста рублей",
    "полтинник": "пятьдесят рублей",
}


def _normalize_slang(text: str) -> str:
    for slang, normal in _SLANG_MAP.items():
        text = re.sub(rf"\b{slang}\b", normal, text)
    return text


def split_text_and_amount(text: str) -> tuple[str, float | None, str | None]:
    """Извлекает описание, сумму и валюту из текста."""
    morph = natasha.MorphVocab()
    extractor = natasha.MoneyExtractor(morph)

    text = text.lower().strip()
    text = _normalize_slang(text)
    matches = list(extractor(text))

    if not matches:
        return text, None, None

    match = matches[0]
    amount = match.fact.amount
    currency = match.fact.currency or "RUB"

    if hasattr(match, "span"):
        start, end = match.span
    elif hasattr(match, "start") and hasattr(match, "stop"):
        start, end = match.start, match.stop
    else:
        found = re.search(r"\d+[.,]?\d*\s*руб", text)
        start, end = found.span() if found else (len(text), len(text))

    description = text[:start].strip(" ,.")

    if not description:
        desc_match = re.search(r"(.+?)\s+\d+[.,]?\d*\s*руб", text)
        if desc_match:
            description = desc_match.group(1)

    return description, amount, currency
