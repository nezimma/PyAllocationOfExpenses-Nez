# services/challenge_analysis_service.py — анализ расходов и генерация предложений челленджей
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

CATEGORY_LABELS: dict[str, str] = {
    "restaurants":   "Рестораны и еда",
    "transport":     "Транспорт",
    "housing":       "Жильё",
    "household":     "Быт",
    "clothes":       "Одежда",
    "electronics":   "Техника",
    "education":     "Образование",
    "entertainment": "Развлечения",
    "health":        "Здоровье",
}

CATEGORY_EMOJIS: dict[str, str] = {
    "restaurants":   "🍽",
    "transport":     "🚗",
    "housing":       "🏠",
    "household":     "🧹",
    "clothes":       "👗",
    "electronics":   "💻",
    "education":     "📚",
    "entertainment": "🎮",
    "health":        "💊",
}

# Категории, для которых не предлагаем челлендж (разовые крупные платежи)
_SKIP_CATS = {"housing", "electronics", "education"}

# Минимальная средняя месячная трата для предложения (иначе неинтересно)
_MIN_AVG = 80.0

# Минимум месяцев с тратами (чтобы были данные для паттерна)
_MIN_MONTHS = 2


@dataclass
class ChallengeProposal:
    category_key: str
    category_label: str
    category_emoji: str
    avg_monthly: float           # средняя трата за прошлые месяцы
    suggested_limit: float       # рекомендуемый лимит (avg * 0.75, округлён до 10)
    current_month_spent: float   # уже потрачено в текущем месяце


def suggest_challenges(
    expenses: list[dict],
    active_cats: set[str],
) -> list[ChallengeProposal]:
    """
    Анализирует список расходов (формат API: {cat, amount, date, ...})
    и возвращает предложения финансовых вызовов.

    active_cats — категории с уже активным вызовом (пропускаются).
    """
    now = date.today()
    current_month = (now.year, now.month)

    # Группируем суммы по (категория, год-месяц)
    cat_monthly: dict[str, dict[tuple[int, int], float]] = defaultdict(lambda: defaultdict(float))

    for exp in expenses:
        cat = exp.get("cat", "other")
        if cat in _SKIP_CATS or cat in active_cats or cat == "other":
            continue
        try:
            d = date.fromisoformat(str(exp.get("date", ""))[:10])
        except (ValueError, TypeError):
            continue
        cat_monthly[cat][(d.year, d.month)] += float(exp.get("amount") or 0)

    proposals = []
    for cat, monthly in cat_monthly.items():
        if cat not in CATEGORY_LABELS:
            continue

        past = {k: v for k, v in monthly.items() if k != current_month}
        current_spent = monthly.get(current_month, 0.0)

        if len(past) < _MIN_MONTHS:
            continue

        avg = sum(past.values()) / len(past)
        if avg < _MIN_AVG:
            continue

        # Предлагаем сэкономить 25%, округляем до 10
        suggested = round(avg * 0.75 / 10) * 10
        suggested = max(suggested, 50.0)

        proposals.append(ChallengeProposal(
            category_key=cat,
            category_label=CATEGORY_LABELS[cat],
            category_emoji=CATEGORY_EMOJIS.get(cat, "💰"),
            avg_monthly=round(avg, 2),
            suggested_limit=float(suggested),
            current_month_spent=round(current_spent, 2),
        ))

    # По убыванию средней траты — самые значимые категории первыми
    proposals.sort(key=lambda p: p.avg_monthly, reverse=True)
    return proposals
