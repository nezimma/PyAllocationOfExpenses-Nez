# database/text_parser.py — парсинг суммы и описания из распознанного текста
import re
import logging
import natasha

logger = logging.getLogger(__name__)

_SLANG_MAP = {
    # ── круглые суммы → цифры (natasha понимает только цифры) ─
    "пятёрку":      "5 рублей",
    "пятерку":      "5 рублей",
    "пятак":        "5 рублей",
    "десятку":      "10 рублей",
    "десятак":      "10 рублей",
    "двадцатку":    "20 рублей",
    "двадцатка":    "20 рублей",
    "тридцатку":    "30 рублей",
    "сорокет":      "40 рублей",
    "полтинник":    "50 рублей",
    "полста":       "50 рублей",
    "полтос":       "50 рублей",
    "шестидесятку": "60 рублей",
    "семидесятку":  "70 рублей",
    "восьмидесятку":"80 рублей",
    "девяностник":  "90 рублей",
    "сотку":        "100 рублей",
    "сотка":        "100 рублей",
    "стольник":     "100 рублей",
    "двушку":       "200 рублей",
    "двушка":       "200 рублей",
    "трёшку":       "300 рублей",
    "трёшка":       "300 рублей",
    "трешку":       "300 рублей",
    "пятихатку":    "500 рублей",
    "пятихатка":    "500 рублей",
    "пятисотку":    "500 рублей",
    # ── тысячи ───────────────────────────────────────────────
    "тыщу":         "1000 рублей",
    "тыщщу":        "1000 рублей",
    "тысячку":      "1000 рублей",
    "штуку":        "1000 рублей",
    "штука":        "1000 рублей",
    "косарь":       "1000 рублей",
    "косаря":       "1000 рублей",
    "косарей":      "1000 рублей",
    "кусок":        "1000 рублей",
    "куска":        "1000 рублей",
    "кусков":       "1000 рублей",
    # ── разговорные формы слова "рубль" ──────────────────────
    # (заменяем на "рублей" — natasha найдёт число перед ним)
    "рубасиков":    "рублей",
    "рубасов":      "рублей",
    "рублёв":       "рублей",
    "рублёвых":     "рублей",
    "рублёчков":    "рублей",
    "рублюшек":     "рублей",
    "рубчиков":     "рублей",
    "рубчик":       "рубль",
    "рубков":       "рублей",
    "деревянных":   "рублей",
    "тыщ":          "рублей",   # "30 тыщ" → "30 рублей" (в белорусском контексте)
}

_STOP_CHARS = ',.*-–()[]{}!&"\\#№:;—«»?'

# Глаголы, с которых обычно начинается описание нового расхода
_ACTION_VERBS = (
    r'взял|взяла|купил|купила|приобрел|приобрела|заказал|заказала'
    r'|поехал|поехала|прокатился|прокатилась|скатался|скаталась'
    r'|вызвал|вызвала|оплатил|оплатила|заплатил|заплатила'
    r'|зашёл|зашел|зашла|сходил|сходила'
    r'|арендовал|арендовала|заправил|заправила'
    r'|посидел|посидела|побывал|побывала'
    r'|пошёл|пошел|пошла|пошли'
    r'|забрал|забрала|забрали'
    r'|прошёлся|прошелся|прошлась'
    r'|отдал|отдала|отдали'
    r'|снял|сняла'
    r'|взяла|взял'
)

# Разделители между расходами (применяются к GAP-у между двумя суммами):
#   1. граница предложения: ". " / "! " / "? "
#   2. союзы: "а также", "плюс", "потом", "ещё"  (не "и" — слишком широко)
#   3. глагол нового действия: " купил", " пошла" и т.д.
#   4. начало нового места/магазина: " в магазин", " на вб"
_SEP_RE = re.compile(
    r'[.!?]\s+'
    r'|\s+(?:а также|плюс|потом|ещё|еще)\s+'
    rf'|\s+(?:{_ACTION_VERBS})\b'
    r'|\s+(?:в магазин|на вб|на wildberries|в аптек|на заправк|в кафе|в ресторан)',
    re.IGNORECASE,
)

# "два шестьдесят девять" → "два рубля шестьдесят девять копейки" (разговорный формат цены)
_ONES = r'(?:один|одна|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|одиннадцать|двенадцать|тринадцать|четырнадцать|пятнадцать|шестнадцать|семнадцать|восемнадцать|девятнадцать)'
_TENS = r'(?:двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто)'
# Два паттерна без optional-группы, чтобы избежать бэктрекинга через lookahead:
# 1) X десятки единицы  (три девяносто девять)
# 2) X десятки          (пять двадцать), только если дальше не стоит ещё одно числительное
_KOPECK_RE_FULL = re.compile(rf'\b({_ONES})\s+({_TENS}\s+{_ONES})(?!\s*рубл)', re.IGNORECASE)
_KOPECK_RE_TENS = re.compile(rf'\b({_ONES})\s+({_TENS})(?!\s*(?:рубл|{_ONES}))', re.IGNORECASE)


def _normalize_slang(text: str) -> str:
    for slang, normal in _SLANG_MAP.items():
        text = re.sub(rf"\b{slang}\b", normal, text)
    return text


def _normalize_kopecks(text: str) -> str:
    """'два шестьдесят девять' → 'два рубля шестьдесят девять копейки'."""
    text = _KOPECK_RE_FULL.sub(lambda m: f"{m.group(1)} рубля {m.group(2)} копейки", text)
    text = _KOPECK_RE_TENS.sub(lambda m: f"{m.group(1)} рубля {m.group(2)} копейки", text)
    return text


def _get_span(match) -> tuple[int, int]:
    if hasattr(match, "span"):
        return match.span
    return match.start, match.stop


def _clean_desc(text: str) -> str:
    for ch in _STOP_CHARS:
        text = text.replace(ch, "")
    return text.strip()


def split_text_and_amount(text: str) -> tuple[str, float | None, str | None]:
    """Извлекает описание, сумму и валюту из текста."""
    morph = natasha.MorphVocab()
    extractor = natasha.MoneyExtractor(morph)

    text = text.lower().strip()
    text = _normalize_slang(text)
    text = _normalize_kopecks(text)
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


def split_multi_expenses(text: str) -> list[tuple[str, float | None, str | None]]:
    """
    Разбивает текст на несколько расходов если найдено несколько сумм.
    Возвращает список (описание, сумма, валюта).
    """
    morph = natasha.MorphVocab()
    extractor = natasha.MoneyExtractor(morph)

    text = text.lower().strip()
    text = _normalize_slang(text)
    text = _normalize_kopecks(text)
    matches = list(extractor(text))

    if not matches:
        return [(text, None, None)]

    if len(matches) == 1:
        desc, amount, currency = split_text_and_amount(text)
        return [(desc, amount, currency)]

    # Находим границы сегментов между соседними суммами
    boundaries = [0]
    for i in range(len(matches) - 1):
        _, end1 = _get_span(matches[i])
        start2, _ = _get_span(matches[i + 1])
        gap = text[end1:start2]
        sep = _SEP_RE.search(gap)
        if sep:
            boundaries.append(end1 + sep.start())
        else:
            # Нет явного разделителя — граница сразу после конца предыдущей суммы.
            # Описание следующего расхода начинается с первого слова в gap'е.
            boundaries.append(end1)
    boundaries.append(len(text))

    result = []
    for i, match in enumerate(matches):
        seg_start = boundaries[i]
        seg_end = boundaries[i + 1]
        seg = text[seg_start:seg_end].strip()

        amount = match.fact.amount
        currency = match.fact.currency or "RUB"

        abs_start, abs_end = _get_span(match)
        rel_start = max(0, min(abs_start - seg_start, len(seg)))
        rel_end = max(0, min(abs_end - seg_start, len(seg)))

        desc = (seg[:rel_start] + seg[rel_end:]).strip(" ,.")
        desc = _clean_desc(desc) or seg

        result.append((desc, amount, currency))

    return result
