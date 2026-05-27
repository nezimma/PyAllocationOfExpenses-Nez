# services/challenge_service.py — оркестратор геймификации
import calendar
import logging
from datetime import date, datetime, timedelta

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database
from services.challenge_analysis_service import (
    suggest_challenges,
    ChallengeProposal,
    CATEGORY_LABELS,
    CATEGORY_EMOJIS,
    _SKIP_CATS,
)

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _period_for_current_month() -> tuple[date, date]:
    today = date.today()
    start = date(today.year, today.month, 1)
    last = calendar.monthrange(today.year, today.month)[1]
    end = date(today.year, today.month, last)
    return start, end


def _next_notify_at(days_left: int) -> datetime:
    """Следующий момент проверки в зависимости от оставшихся дней."""
    base = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
    if days_left <= 3:
        return base + timedelta(hours=12)
    if days_left <= 7:
        return base + timedelta(days=1)
    return base + timedelta(days=3)


def _progress_bar(pct: int) -> str:
    filled = min(10, pct // 10)
    return "█" * filled + "░" * (10 - filled)


# ── Публичные функции ─────────────────────────────────────────────────────────

async def accept_challenge(
    telegram_id: int,
    category_key: str,
    target_amount: float,
) -> int:
    """Создаёт вызов и возвращает challenge_id."""
    cat_label = CATEGORY_LABELS.get(category_key, category_key)
    period_start, period_end = _period_for_current_month()
    title = f"{cat_label}: до {target_amount:,.0f} Br"
    today = date.today()
    days_left = (period_end - today).days
    next_notify = _next_notify_at(days_left)

    # Вычисляем avg_amount для записи (без блокировки, если не получится — None)
    avg_amount = None
    try:
        expenses = await database.expenses.get_expenses_for_api(telegram_id)
        active_cats = await database.challenges.get_active_challenge_categories(telegram_id)
        proposals = suggest_challenges(expenses, active_cats)
        prop = next((p for p in proposals if p.category_key == category_key), None)
        avg_amount = prop.avg_monthly if prop else None
    except Exception:
        pass

    challenge_id = await database.challenges.create_challenge(
        telegram_id=telegram_id,
        category_key=category_key,
        category_label=cat_label,
        title=title,
        target_amount=target_amount,
        currency="BYN",
        period_start=period_start,
        period_end=period_end,
        avg_amount=avg_amount,
        next_notify_at=next_notify,
    )

    # Достижение «Железная воля» — принял вызов после провала
    try:
        if await database.challenges.had_recent_failed_challenge(telegram_id):
            user_id = await database.challenges.get_user_id_by_telegram(telegram_id)
            if user_id:
                earned = await database.challenges.award_achievement(
                    user_id, "iron_will", challenge_id
                )
                logger.info(f"iron_will for {telegram_id}: {earned}")
    except Exception:
        logger.exception("award iron_will failed")

    return challenge_id


async def maybe_propose(telegram_id: int, category_key: str, bot: Bot) -> None:
    """
    Вызывается после записи расхода. Если это первый расход месяца
    в данной категории и есть история ≥ 2 мес — предлагает вызов.
    """
    if category_key in _SKIP_CATS or category_key == "other":
        return

    cat_label = CATEGORY_LABELS.get(category_key)
    if not cat_label:
        return

    try:
        # Первый расход этого месяца в категории?
        if not await database.challenges.is_first_expense_this_month(telegram_id, cat_label):
            return

        # Нет активного вызова?
        active_cats = await database.challenges.get_active_challenge_categories(telegram_id)
        if category_key in active_cats:
            return

        # Достаточно истории?
        months = await database.challenges.count_spending_months(telegram_id, cat_label)
        if months < 2:
            return

        # Строим предложение
        expenses = await database.expenses.get_expenses_for_api(telegram_id)
        proposals = suggest_challenges(expenses, active_cats)
        proposal = next((p for p in proposals if p.category_key == category_key), None)
        if not proposal:
            return

        await _send_proposal(telegram_id, proposal, bot)

    except Exception:
        logger.exception(f"maybe_propose failed for {telegram_id}/{category_key}")


async def _send_proposal(telegram_id: int, proposal: ChallengeProposal, bot: Bot) -> None:
    today = date.today()
    yyyymm = f"{today.year}{today.month:02d}"
    target_int = int(proposal.suggested_limit)

    text = (
        f"🎯 <b>Финансовый вызов!</b>\n\n"
        f"Замечаю, что в среднем тратишь "
        f"<b>~{proposal.avg_monthly:,.0f} Br/мес</b> "
        f"на {proposal.category_emoji} <b>{proposal.category_label}</b>.\n\n"
        f"Цель: уложиться в <b>{proposal.suggested_limit:,.0f} Br</b> до конца месяца."
    )
    if proposal.current_month_spent > 0:
        text += (
            f"\n\n💡 В этом месяце уже потрачено: "
            f"<b>{proposal.current_month_spent:,.0f} Br</b>"
        )

    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Принять",
        callback_data=f"ch_accept:{proposal.category_key}:{target_int}:{yyyymm}",
    )
    kb.button(
        text="✏️ Свой лимит",
        callback_data=f"ch_custom:{proposal.category_key}:{yyyymm}",
    )
    kb.button(text="❌ Не сейчас", callback_data="ch_decline")
    kb.adjust(2, 1)

    await bot.send_message(
        telegram_id, text, reply_markup=kb.as_markup(), parse_mode="HTML"
    )


# ── Планировщик: прогресс ─────────────────────────────────────────────────────

async def send_progress_notifications(bot: Bot) -> None:
    """Вызывается из планировщика каждые 30 сек."""
    try:
        due = await database.challenges.get_due_challenges()
    except Exception:
        logger.exception("get_due_challenges failed")
        return

    for row in due:
        try:
            await _process_due_challenge(row, bot)
        except Exception:
            logger.exception(f"progress notify failed for challenge {row.get('challenge_id')}")


async def _process_due_challenge(row: dict, bot: Bot) -> None:
    cid = row["challenge_id"]
    telegram_id = row["telegram_id"]
    target = float(row["target_amount"])
    spent = float(row["spent_amount"])
    notified_pct = int(row.get("notified_pct") or 0)

    if target <= 0:
        await database.challenges.advance_notify(cid)
        return

    pct = int(spent / target * 100)
    period_end = date.fromisoformat(row["period_end"][:10])
    days_left = (period_end - date.today()).days
    remaining = max(0.0, target - spent)
    sym = "Br"

    if pct >= 80 and notified_pct < 80:
        new_pct = 80
        text = (
            f"⚠️ <b>Вызов: {row['category_label']}</b>\n\n"
            f"{_progress_bar(pct)} <b>{pct}%</b>\n"
            f"Потрачено: <b>{spent:,.0f}</b> из {target:,.0f} {sym}\n"
            f"Осталось: <b>{remaining:,.0f} {sym}</b> на {days_left} дн.\n\n"
            f"Аккуратнее — почти весь лимит! 😬"
        )
    elif pct >= 50 and notified_pct < 50:
        new_pct = 50
        text = (
            f"📊 <b>Вызов: {row['category_label']}</b>\n\n"
            f"{_progress_bar(pct)} <b>{pct}%</b>\n"
            f"Потрачено: <b>{spent:,.0f}</b> из {target:,.0f} {sym}\n"
            f"Осталось: <b>{remaining:,.0f} {sym}</b> на {days_left} дн.\n\n"
            f"Держишься хорошо! 💪"
        )
    elif days_left <= 3 and notified_pct < 90:
        new_pct = 90
        finish = "Финишная прямая!" if pct < 100 else "⚠️ Лимит уже превышен!"
        text = (
            f"🏁 <b>Вызов: {row['category_label']}</b>\n\n"
            f"До конца <b>{days_left} дн.</b> {finish}\n"
            f"{_progress_bar(pct)} {pct}%\n"
            f"Потрачено: {spent:,.0f} из {target:,.0f} {sym}"
        )
    else:
        await database.challenges.advance_notify(cid)
        return

    await bot.send_message(telegram_id, text, parse_mode="HTML")
    next_nfy = _next_notify_at(days_left)
    await database.challenges.update_challenge_notify(cid, new_pct, next_nfy)
    logger.info(f"Challenge {cid} → {telegram_id}: progress {pct}% notified")


# ── Планировщик: финализация ──────────────────────────────────────────────────

async def finalize_all_challenges(bot: Bot) -> None:
    """Закрывает истёкшие вызовы и выдаёт достижения."""
    try:
        expired = await database.challenges.get_expired_challenges()
    except Exception:
        logger.exception("get_expired_challenges failed")
        return

    for row in expired:
        try:
            await _finalize_one(row, bot)
        except Exception:
            logger.exception(f"finalize failed for challenge {row.get('challenge_id')}")


async def _finalize_one(row: dict, bot: Bot) -> None:
    cid = row["challenge_id"]
    telegram_id = row["telegram_id"]
    target = float(row["target_amount"])
    spent = float(row["spent_amount"])
    avg = float(row.get("avg_amount") or target)

    success = spent <= target
    status = "success" if success else "failed"
    await database.challenges.finalize_challenge(cid, status)

    if success:
        pct_used = int(spent / target * 100) if target > 0 else 0
        saved = round(avg - spent, 0)
        text = (
            f"🏆 <b>Вызов выполнен!</b>\n\n"
            f"{row['category_label']} — цель достигнута!\n"
            f"{_progress_bar(pct_used)} {pct_used}%\n"
            f"Потрачено: <b>{spent:,.0f}</b> / {target:,.0f} Br\n\n"
        )
        if saved > 0:
            text += f"Ты сэкономил <b>~{saved:,.0f} Br</b> по сравнению со средним! 🎉"
    else:
        over = spent - target
        text = (
            f"💸 <b>Вызов завершён</b>\n\n"
            f"{row['category_label']} — лимит превышен на <b>{over:,.0f} Br</b>.\n"
            f"Потрачено: {spent:,.0f} / {target:,.0f} Br\n\n"
            f"Не расстраивайся — в следующий раз получится! 💪"
        )

    await bot.send_message(telegram_id, text, parse_mode="HTML")

    # Достижения
    try:
        user_id = await database.challenges.get_user_id_by_telegram(telegram_id)
        if user_id:
            await _check_and_award(telegram_id, user_id, cid, success, spent, target, avg, bot)
    except Exception:
        logger.exception(f"award achievements failed for challenge {cid}")


async def _check_and_award(
    telegram_id: int,
    user_id: int,
    cid: int,
    success: bool,
    spent: float,
    target: float,
    avg: float,
    bot: Bot,
) -> None:
    earned: list[tuple[str, str]] = []

    if success:
        if await database.challenges.award_achievement(user_id, "first_win", cid):
            earned.append(("🏆", "Первая победа"))

        if avg - spent >= 500:
            if await database.challenges.award_achievement(user_id, "big_save", cid):
                earned.append(("💰", "Большая экономия"))

        if target > 0 and spent / target < 0.5:
            if await database.challenges.award_achievement(user_id, "under_50", cid):
                earned.append(("🎯", "С большим запасом"))

        if spent == 0:
            if await database.challenges.award_achievement(user_id, "no_spend", cid):
                earned.append(("🌟", "Ноль трат"))

        streak = await database.challenges.get_success_streak(telegram_id)
        if streak >= 5:
            if await database.challenges.award_achievement(user_id, "saver_5", cid):
                earned.append(("🥇", "Мастер бюджета"))
        elif streak >= 3:
            if await database.challenges.award_achievement(user_id, "saver_3", cid):
                earned.append(("🥉", "Экономный ×3"))

    if earned:
        lines = "\n".join(f"{icon} <b>{name}</b>" for icon, name in earned)
        await bot.send_message(
            telegram_id,
            f"🎊 <b>Новые достижения!</b>\n\n{lines}",
            parse_mode="HTML",
        )
        logger.info(f"Achievements for {telegram_id}: {[n for _, n in earned]}")
