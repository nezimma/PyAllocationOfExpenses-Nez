# services/forecast_service.py — прогноз расходов на конец месяца
import calendar
from datetime import date
from collections import defaultdict

import numpy as np
from sklearn.linear_model import LinearRegression

MIN_DAYS_FOR_REGRESSION = 5  # меньше — используем простое среднее


def forecast_month(
    daily_rows: list[tuple[date, float, str]],  # (day, amount, category)
    year: int,
    month: int,
) -> dict:
    """
    Прогнозирует итог месяца по дневным тратам.

    Возвращает словарь:
      total_spent       — уже потрачено
      forecast_total    — прогноз на конец месяца
      daily_avg         — среднедневной расход
      days_elapsed      — прошло дней с тратами
      days_in_month     — всего дней в месяце
      days_remaining    — осталось дней
      method            — 'regression' | 'average'
      r2                — R² (только при regression, иначе None)
      by_category       — {category: forecast_amount}
      enough_data       — True если данных достаточно для прогноза
    """
    days_in_month = calendar.monthrange(year, month)[1]
    today = date.today()
    if today.year == year and today.month == month:
        current_day = today.day
    else:
        current_day = days_in_month  # прошлый месяц — используем все дни

    # Группируем по дням
    by_day: dict[int, float] = defaultdict(float)
    by_day_cat: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for day, amount, category in daily_rows:
        d = day if isinstance(day, int) else day.day
        by_day[d] += amount
        by_day_cat[d][category or "other"] += amount

    if not by_day:
        return _empty_result(days_in_month, current_day)

    total_spent = sum(by_day.values())
    days_with_data = sorted(by_day.keys())
    days_elapsed = len(days_with_data)

    # Кумулятивные суммы по дням для регрессии
    cum = []
    running = 0.0
    for d in range(1, current_day + 1):
        running += by_day.get(d, 0.0)
        cum.append((d, running))

    daily_avg = total_spent / current_day  # среднее по всем дням периода
    days_remaining = days_in_month - current_day

    # Выбираем метод
    if days_elapsed >= MIN_DAYS_FOR_REGRESSION and len(cum) >= MIN_DAYS_FOR_REGRESSION:
        X = np.array([c[0] for c in cum]).reshape(-1, 1)
        y = np.array([c[1] for c in cum])
        model = LinearRegression().fit(X, y)
        forecast_total = float(model.predict([[days_in_month]])[0])
        r2 = float(model.score(X, y))
        method = "regression"
        # Не даём прогнозу быть меньше уже потраченного
        forecast_total = max(forecast_total, total_spent)
    else:
        forecast_total = daily_avg * days_in_month
        r2 = None
        method = "average"

    # Прогноз по категориям — простое масштабирование
    by_cat_total: dict[str, float] = defaultdict(float)
    for d_cats in by_day_cat.values():
        for cat, amt in d_cats.items():
            by_cat_total[cat] += amt

    scale = forecast_total / total_spent if total_spent > 0 else 1.0
    by_category = {cat: round(amt * scale, 2) for cat, amt in by_cat_total.items()}
    by_category = dict(sorted(by_category.items(), key=lambda x: -x[1]))

    return {
        "total_spent":    round(total_spent, 2),
        "forecast_total": round(forecast_total, 2),
        "daily_avg":      round(daily_avg, 2),
        "days_elapsed":   current_day,
        "days_in_month":  days_in_month,
        "days_remaining": days_remaining,
        "method":         method,
        "r2":             round(r2, 3) if r2 is not None else None,
        "by_category":    by_category,
        "enough_data":    days_elapsed >= 3,
    }


def _empty_result(days_in_month: int, current_day: int) -> dict:
    return {
        "total_spent":    0.0,
        "forecast_total": 0.0,
        "daily_avg":      0.0,
        "days_elapsed":   current_day,
        "days_in_month":  days_in_month,
        "days_remaining": days_in_month - current_day,
        "method":         "average",
        "r2":             None,
        "by_category":    {},
        "enough_data":    False,
    }
