# bot/routers/challenges.py — финансовые вызовы и достижения
import logging
from datetime import date

from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database
from bot.states import BotState
from services import challenge_service
from services.challenge_analysis_service import (
    suggest_challenges,
    CATEGORY_LABELS,
    CATEGORY_EMOJIS,
)

router = Router()
logger = logging.getLogger(__name__)


# ── Главный экран вызовов ──────────────────────────────────────────────────────

@router.message(F.text == "🎯 Вызовы")
@router.message(Command("challenges"))
async def cmd_challenges(message: types.Message):
    await _show_challenges(message.from_user.id, message)


async def _show_challenges(telegram_id: int, message: types.Message) -> None:
    active = await database.challenges.get_active_challenges(telegram_id)

    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Предложи вызов", callback_data="ch_propose")
    kb.button(text="🏆 Достижения", callback_data="ch_achievements")
    kb.adjust(1)

    if not active:
        await message.answer(
            "🎯 <b>Финансовые вызовы</b>\n\n"
            "Нет активных вызовов.\n"
            "Запиши несколько трат — и я предложу цель автоматически.\n"
            "Или нажми кнопку ниже, чтобы найти вызов прямо сейчас.",
            reply_markup=kb.as_markup(),
            parse_mode="HTML",
        )
        return

    lines = []
    for ch in active:
        target = float(ch["target_amount"])
        spent = float(ch["spent_amount"])
        pct = int(spent / target * 100) if target > 0 else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        remaining = max(0.0, target - spent)
        period_end = date.fromisoformat(ch["period_end"][:10])
        days_left = (period_end - date.today()).days
        emoji = CATEGORY_EMOJIS.get(ch["category_key"], "🎯")
        lines.append(
            f"{emoji} <b>{ch['category_label']}</b>\n"
            f"{bar} {pct}%\n"
            f"{spent:,.0f} / {target:,.0f} Br · осталось {remaining:,.0f} Br, {days_left} дн."
        )

    text = "🎯 <b>Активные вызовы</b>\n\n" + "\n\n".join(lines)
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


# ── Предложить вызов по запросу ────────────────────────────────────────────────

@router.callback_query(F.data == "ch_propose")
async def cb_propose(callback: types.CallbackQuery, bot: Bot):
    await callback.answer()
    telegram_id = callback.from_user.id

    active_cats = await database.challenges.get_active_challenge_categories(telegram_id)
    expenses = await database.expenses.get_expenses_for_api(telegram_id)
    proposals = suggest_challenges(expenses, active_cats)

    if not proposals:
        await callback.message.answer(
            "🔍 Пока недостаточно данных.\n"
            "Нужно минимум 2 месяца трат по одной категории — продолжай записывать расходы! 📝"
        )
        return

    sent = 0
    for p in proposals[:3]:
        await challenge_service._send_proposal(telegram_id, p, bot)
        sent += 1

    if sent == 0:
        await callback.message.answer("🔍 Нет новых предложений — все категории уже охвачены вызовами.")


# ── Достижения ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "ch_achievements")
async def cb_achievements(callback: types.CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id

    all_ach = await database.challenges.get_all_achievements()
    user_ach = await database.challenges.get_user_achievements_for_api(telegram_id)
    earned_codes = {a["code"] for a in user_ach}

    if not user_ach:
        locked = "\n".join(
            f"🔒 {a['icon']} {a['title']} — {a['description']}" for a in all_ach
        )
        await callback.message.answer(
            f"🏆 <b>Достижения</b>\n\n"
            f"Пока нет заработанных — прими первый вызов!\n\n"
            f"<b>Доступные ({len(all_ach)}):</b>\n{locked}",
            parse_mode="HTML",
        )
        return

    earned_lines = "\n".join(
        f"✅ {a['icon']} <b>{a['title']}</b> — {a['description']}"
        for a in all_ach if a["code"] in earned_codes
    )
    locked_lines = "\n".join(
        f"🔒 {a['icon']} {a['title']} — {a['description']}"
        for a in all_ach if a["code"] not in earned_codes
    )
    text = (
        f"🏆 <b>Достижения ({len(user_ach)}/{len(all_ach)})</b>\n\n"
        f"{earned_lines}"
    )
    if locked_lines:
        text += f"\n\n<b>Ещё можно получить:</b>\n{locked_lines}"

    await callback.message.answer(text, parse_mode="HTML")


# ── Принять вызов ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ch_accept:"))
async def cb_accept(callback: types.CallbackQuery):
    await callback.answer("✅ Вызов принят!")

    parts = callback.data.split(":")
    # ch_accept:{cat_key}:{target_int}:{yyyymm}
    cat_key = parts[1]
    target = float(parts[2])

    active_cats = await database.challenges.get_active_challenge_categories(callback.from_user.id)
    if cat_key in active_cats:
        await callback.message.answer("⚠️ У тебя уже есть активный вызов по этой категории.")
        return

    challenge_id = await challenge_service.accept_challenge(
        callback.from_user.id, cat_key, target
    )

    label = CATEGORY_LABELS.get(cat_key, cat_key)
    emoji = CATEGORY_EMOJIS.get(cat_key, "🎯")
    today = date.today()
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    period_end = date(today.year, today.month, last_day)
    days_left = (period_end - today).days

    await callback.message.answer(
        f"🎯 <b>Вызов принят!</b>\n\n"
        f"{emoji} <b>{label}</b>\n"
        f"Лимит: <b>{target:,.0f} Br</b> до конца месяца\n"
        f"Осталось дней: {days_left}\n\n"
        f"Буду следить за прогрессом и сообщать! 💪",
        parse_mode="HTML",
    )
    try:
        await callback.message.delete()
    except Exception:
        pass


# ── Свой лимит (FSM) ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ch_custom:"))
async def cb_custom(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    cat_key = parts[1]

    label = CATEGORY_LABELS.get(cat_key, cat_key)
    await state.update_data(challenge_cat_key=cat_key)
    await state.set_state(BotState.waiting_for_challenge_limit)
    await callback.message.answer(
        f"✏️ Введи свой лимит для <b>{label}</b> (в Br):\n"
        f"Например: <code>1200</code>",
        parse_mode="HTML",
    )


@router.message(BotState.waiting_for_challenge_limit, F.text)
async def receive_challenge_limit(message: types.Message, state: FSMContext):
    text = message.text.strip().replace(",", ".")
    try:
        limit = float(text)
        if limit <= 0:
            raise ValueError("non-positive")
    except ValueError:
        await message.answer("❌ Введи положительное число. Например: <code>1200</code>", parse_mode="HTML")
        return

    data = await state.get_data()
    cat_key = data.get("challenge_cat_key", "")
    await state.clear()

    if not cat_key:
        await message.answer("❌ Что-то пошло не так. Попробуй снова через «🎯 Вызовы».")
        return

    active_cats = await database.challenges.get_active_challenge_categories(message.from_user.id)
    if cat_key in active_cats:
        await message.answer("⚠️ У тебя уже есть активный вызов по этой категории.")
        return

    await challenge_service.accept_challenge(message.from_user.id, cat_key, limit)
    label = CATEGORY_LABELS.get(cat_key, cat_key)
    await message.answer(
        f"✅ <b>Вызов создан!</b>\n\n"
        f"{CATEGORY_EMOJIS.get(cat_key, '🎯')} {label}: лимит <b>{limit:,.0f} Br</b> до конца месяца.\n\n"
        f"Удачи! Буду следить за прогрессом 💪",
        parse_mode="HTML",
    )


# ── Отклонить предложение ─────────────────────────────────────────────────────

@router.callback_query(F.data == "ch_decline")
async def cb_decline(callback: types.CallbackQuery):
    await callback.answer("Окей, в следующий раз 👍")
    try:
        await callback.message.delete()
    except Exception:
        pass
