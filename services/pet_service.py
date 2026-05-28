# services/pet_service.py — XP-логика для питомца-тамагочи
import logging
import math
from datetime import timezone, datetime

import database

logger = logging.getLogger(__name__)

# ── XP за события ────────────────────────────────────────────────────────────
XP_EXPENSE          = 15
XP_CHALLENGE_ACCEPT = 50
XP_CHALLENGE_WIN    = 200
XP_ACHIEVEMENT      = 75


# ── Формулы ──────────────────────────────────────────────────────────────────

def level_from_xp(xp: int) -> int:
    if xp <= 0:
        return 1
    return max(1, int((1 + math.sqrt(1 + 4 * xp / 50)) / 2))


def xp_for_level(level: int) -> int:
    """Минимальный XP для достижения уровня level."""
    return 50 * level * (level - 1)


def stage_from_level(level: int) -> int:
    """Визуальная стадия пришельца (1-5)."""
    if level <= 2:  return 1   # 🛸 UFO
    if level <= 5:  return 2   # зелёный малыш
    if level <= 10: return 3   # синий средний
    if level <= 15: return 4   # фиолетовый большой
    return 5                   # золотой космический лорд


def env_from_streak(streak: int) -> int:
    """Фон окружения (0-3) по количеству дней подряд."""
    if streak <= 2:  return 0   # тёмный космос
    if streak <= 6:  return 1   # планета рядом
    if streak <= 20: return 2   # туманность
    return 3                    # ядро галактики


def _animation(last_event: str, hours_ago: float | None) -> str:
    if hours_ago is None or hours_ago > 72:
        return "sleeping"
    if hours_ago < 2 and last_event == "expense":
        return "eating"
    if hours_ago < 24 and last_event in ("challenge_complete", "achievement"):
        return "celebrating"
    return "idle"


# ── Публичные функции ─────────────────────────────────────────────────────────

async def on_expense_saved(telegram_id: int) -> None:
    try:
        await database.pet.add_xp(telegram_id, XP_EXPENSE, event="expense")
    except Exception:
        logger.exception(f"pet.on_expense_saved failed for {telegram_id}")


async def on_challenge_accepted(telegram_id: int) -> None:
    try:
        await database.pet.add_xp(telegram_id, XP_CHALLENGE_ACCEPT, event="challenge_accept")
    except Exception:
        logger.exception(f"pet.on_challenge_accepted failed for {telegram_id}")


async def on_challenge_completed(telegram_id: int) -> None:
    try:
        await database.pet.add_xp(telegram_id, XP_CHALLENGE_WIN, event="challenge_complete")
    except Exception:
        logger.exception(f"pet.on_challenge_completed failed for {telegram_id}")


async def on_achievement_earned(telegram_id: int) -> None:
    try:
        await database.pet.add_xp(telegram_id, XP_ACHIEVEMENT, event="achievement")
    except Exception:
        logger.exception(f"pet.on_achievement_earned failed for {telegram_id}")


async def get_pet_data(telegram_id: int) -> dict | None:
    pet = await database.pet.get_or_create(telegram_id)
    if not pet:
        return None

    xp        = pet["xp"] or 0
    level     = pet["level"] or 1
    streak    = pet["day_streak"] or 0
    last_evt  = pet["last_event"] or "idle"
    last_act  = pet["last_action_at"]

    hours_ago: float | None = None
    if last_act:
        now = datetime.now(timezone.utc)
        if last_act.tzinfo is None:
            last_act = last_act.replace(tzinfo=timezone.utc)
        hours_ago = (now - last_act).total_seconds() / 3600

    cur_lvl_xp  = xp_for_level(level)
    next_lvl_xp = xp_for_level(level + 1)

    return {
        "level":              level,
        "xp":                 xp,
        "xp_in_level":        xp - cur_lvl_xp,
        "xp_for_next_level":  next_lvl_xp - cur_lvl_xp,
        "day_streak":         streak,
        "entries_this_week":  pet.get("entries_this_week") or 0,
        "stage":              stage_from_level(level),
        "env":                env_from_streak(streak),
        "animation":          _animation(last_evt, hours_ago),
        "last_event":         last_evt,
        "hours_since_action": round(hours_ago, 1) if hours_ago is not None else None,
    }
