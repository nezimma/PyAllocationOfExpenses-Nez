# services/recurring_service.py — детекция регулярных платежей
import re
from datetime import date, timedelta
from collections import defaultdict

# Глаголы и предлоги, которые не несут смысл платежа
_NOISE_WORDS = {
    "купил", "купила", "оплатил", "оплатила", "заплатил", "заплатила",
    "взял", "взяла", "заказал", "заказала", "сходил", "сходила",
    "зашел", "зашла", "посидел", "посидела", "вызвал", "вызвала",
    "прокатился", "прокатилась", "арендовал", "арендовала",
    "в", "на", "за", "по", "до", "из", "и", "а", "с",
}

# Интервалы в днях для каждого типа повторения
_PERIODS = [
    ("weekly",   6,   8,  "еженедельно"),
    ("monthly",  25,  35, "ежемесячно"),
    ("yearly",  340, 390, "ежегодно"),
]


def _normalize(text: str) -> str:
    """Убирает шумовые слова и оставляет суть описания."""
    text = text.lower().strip()
    words = re.split(r"\s+", text)
    words = [w for w in words if w not in _NOISE_WORDS and len(w) > 2]
    return " ".join(words[:5])  # берём первые 5 значимых слов


def _classify_interval(days: float) -> tuple[str, str] | None:
    for key, lo, hi, label in _PERIODS:
        if lo <= days <= hi:
            return key, label
    return None


def detect_recurring(
    expenses: list[dict],
) -> list[dict]:
    """
    Принимает список расходов вида:
      {id, name, cat, amount, currency, date}
    Возвращает список обнаруженных регулярных платежей:
      {description, period_key, period_label, avg_amount, currency,
       count, avg_interval_days, last_date, next_expected, cat}
    """
    # Группируем по нормализованному описанию
    groups: dict[str, list[dict]] = defaultdict(list)
    for exp in expenses:
        key = _normalize(exp.get("name") or "")
        if not key:
            continue
        groups[key].append(exp)

    result = []
    for key, items in groups.items():
        if len(items) < 2:
            continue

        # Сортируем по дате
        try:
            items_sorted = sorted(items, key=lambda x: x["date"])
        except Exception:
            continue

        # Вычисляем интервалы между последовательными платежами
        intervals = []
        for i in range(len(items_sorted) - 1):
            d1 = _parse_date(items_sorted[i]["date"])
            d2 = _parse_date(items_sorted[i + 1]["date"])
            if d1 and d2:
                intervals.append((d2 - d1).days)

        if not intervals:
            continue

        avg_interval = sum(intervals) / len(intervals)
        classified = _classify_interval(avg_interval)
        if not classified:
            continue

        period_key, period_label = classified

        avg_amount = sum(float(e.get("amount") or 0) for e in items_sorted) / len(items_sorted)
        last = items_sorted[-1]
        last_date = _parse_date(last["date"])
        next_expected = (last_date + timedelta(days=round(avg_interval))) if last_date else None

        # Берём самое длинное оригинальное описание как отображаемое
        display_name = max(
            (e.get("name") or "" for e in items_sorted), key=len
        )

        result.append({
            "description":      display_name,
            "period_key":       period_key,
            "period_label":     period_label,
            "avg_amount":       round(avg_amount, 2),
            "currency":         last.get("currency", "BYN"),
            "count":            len(items_sorted),
            "avg_interval_days": round(avg_interval),
            "last_date":        str(last_date) if last_date else None,
            "next_expected":    str(next_expected) if next_expected else None,
            "cat":              last.get("cat", "other"),
        })

    # Сортируем: сначала ежемесячные (по убыванию суммы), потом остальные
    order = {"monthly": 0, "weekly": 1, "yearly": 2}
    result.sort(key=lambda x: (order.get(x["period_key"], 9), -x["avg_amount"]))
    return result


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
