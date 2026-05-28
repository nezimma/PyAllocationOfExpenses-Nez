# database/pet_repository.py — CRUD для питомца-тамагочи
import logging
import math
from datetime import date, timedelta, timezone, datetime

import asyncpg

logger = logging.getLogger(__name__)


def _level_from_xp(xp: int) -> int:
    """XP → уровень по формуле: xp_for_level(n) = 50·n·(n-1)."""
    if xp <= 0:
        return 1
    return max(1, int((1 + math.sqrt(1 + 4 * xp / 50)) / 2))


class PetRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _user_id(self, conn, telegram_id: int) -> int | None:
        return await conn.fetchval(
            "SELECT user_id FROM users WHERE telegram_id = $1", telegram_id
        )

    async def get_or_create(self, telegram_id: int) -> dict | None:
        async with self.pool.acquire() as conn:
            uid = await self._user_id(conn, telegram_id)
            if not uid:
                return None
            row = await conn.fetchrow(
                "SELECT * FROM tamagotchi WHERE user_id = $1", uid
            )
            if not row:
                row = await conn.fetchrow(
                    "INSERT INTO tamagotchi (user_id) VALUES ($1) RETURNING *", uid
                )
            return dict(row)

    async def add_xp(
        self,
        telegram_id: int,
        xp_gain: int,
        event: str = "expense",
    ) -> dict | None:
        """
        Добавляет XP, обновляет стрик и уровень.
        Возвращает обновлённый dict с полем 'leveled_up'.
        """
        async with self.pool.acquire() as conn:
            uid = await self._user_id(conn, telegram_id)
            if not uid:
                return None

            row = await conn.fetchrow(
                "SELECT * FROM tamagotchi WHERE user_id = $1", uid
            )
            if not row:
                await conn.execute(
                    "INSERT INTO tamagotchi (user_id) VALUES ($1)", uid
                )
                row = await conn.fetchrow(
                    "SELECT * FROM tamagotchi WHERE user_id = $1", uid
                )

            pet = dict(row)
            today = date.today()
            this_monday = today - timedelta(days=today.weekday())

            # ── Стрик и недельный учёт ──────────────────────────────────────
            day_streak: int = pet["day_streak"] or 0
            entries_this_week: int = pet["entries_this_week"] or 0
            week_start: date | None = pet["week_start"]
            last_entry: date | None = pet["last_entry_date"]

            if week_start is None or week_start < this_monday:
                # Началась новая неделя — проверяем прошлую
                if week_start is not None:
                    # Если прошлая неделя «примыкает» (разрыв = 1 неделя)
                    if week_start >= this_monday - timedelta(weeks=1):
                        if entries_this_week < 4:
                            day_streak = 0   # не набрал 4 записи — стрик слетает
                    else:
                        day_streak = 0       # пропустил ≥2 недель
                entries_this_week = 0
                week_start = this_monday

            # Консекутивные дни
            if last_entry is None:
                day_streak = 1
            elif last_entry == today:
                pass                                      # уже считали сегодня
            elif last_entry == today - timedelta(days=1):
                day_streak += 1                           # вчера был — цепочка
            else:
                day_streak = 1                            # разрыв — сброс

            entries_this_week += 1

            # ── XP и уровень ────────────────────────────────────────────────
            old_level: int = pet["level"] or 1
            cur_xp: int = pet["xp"] or 0

            # Бонус первого действия за день (+25 XP) — только для расходов
            if event == "expense" and (last_entry is None or last_entry < today):
                xp_gain += 25

            new_xp = cur_xp + xp_gain
            new_level = _level_from_xp(new_xp)
            leveled_up = new_level > old_level

            await conn.execute(
                """
                UPDATE tamagotchi
                SET xp               = $1,
                    level            = $2,
                    day_streak       = $3,
                    entries_this_week = $4,
                    week_start       = $5,
                    last_entry_date  = $6,
                    last_event       = $7,
                    last_action_at   = NOW()
                WHERE user_id = $8
                """,
                new_xp, new_level, day_streak, entries_this_week,
                week_start, today, event, uid,
            )

        return {
            "xp": new_xp,
            "level": new_level,
            "day_streak": day_streak,
            "entries_this_week": entries_this_week,
            "leveled_up": leveled_up,
            "old_level": old_level,
        }
