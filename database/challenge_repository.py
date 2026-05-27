# database/challenge_repository.py — CRUD для финансовых вызовов и достижений
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

import asyncpg

logger = logging.getLogger(__name__)


def _to_float(v) -> float:
    """Decimal / int / None → float."""
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _row_to_dict(row) -> dict:
    """asyncpg Record → dict с float/str для Decimal/date/datetime."""
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, Decimal):
            d[k] = float(v)
        elif isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
    return d


class ChallengeRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ── Создание ──────────────────────────────────────────────────────────────

    async def create_challenge(
        self,
        telegram_id: int,
        category_key: str,
        category_label: str,
        title: str,
        target_amount: float,
        currency: str,
        period_start: date,
        period_end: date,
        avg_amount: float | None = None,
        next_notify_at: datetime | None = None,
    ) -> int:
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval(
                "SELECT user_id FROM users WHERE telegram_id = $1", telegram_id
            )
            if not user_id:
                raise ValueError(f"User not found for telegram_id={telegram_id}")
            row = await conn.fetchrow(
                """
                INSERT INTO challenges
                    (user_id, category_key, category_label, title,
                     target_amount, currency, period_start, period_end,
                     avg_amount, next_notify_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                RETURNING challenge_id
                """,
                user_id, category_key, category_label, title,
                Decimal(str(target_amount)), currency,
                period_start, period_end,
                Decimal(str(avg_amount)) if avg_amount is not None else None,
                next_notify_at,
            )
            return row["challenge_id"]

    # ── Чтение ────────────────────────────────────────────────────────────────

    async def get_active_challenges(self, telegram_id: int) -> list[dict]:
        """Активные вызовы с вычисленным spent_amount."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.*,
                    COALESCE((
                        SELECT SUM(e.amount)
                        FROM expenses e
                        JOIN categories cat ON e.category_id = cat.category_id
                        WHERE e.user_id = c.user_id
                          AND cat.name = c.category_label
                          AND e.created_at::date BETWEEN c.period_start AND c.period_end
                    ), 0) AS spent_amount
                FROM challenges c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.telegram_id = $1 AND c.status = 'active'
                ORDER BY c.created_at DESC
                """,
                telegram_id,
            )
        return [_row_to_dict(r) for r in rows]

    async def get_challenges_for_api(self, telegram_id: int) -> list[dict]:
        """Все вызовы (до 20) для Mini App."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.*,
                    COALESCE((
                        SELECT SUM(e.amount)
                        FROM expenses e
                        JOIN categories cat ON e.category_id = cat.category_id
                        WHERE e.user_id = c.user_id
                          AND cat.name = c.category_label
                          AND e.created_at::date BETWEEN c.period_start AND c.period_end
                    ), 0) AS spent_amount
                FROM challenges c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.telegram_id = $1
                ORDER BY c.created_at DESC
                LIMIT 20
                """,
                telegram_id,
            )
        return [_row_to_dict(r) for r in rows]

    async def get_active_challenge_categories(self, telegram_id: int) -> set[str]:
        """Категории с активным вызовом у пользователя."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.category_key
                FROM challenges c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.telegram_id = $1 AND c.status = 'active'
                """,
                telegram_id,
            )
        return {r["category_key"] for r in rows}

    async def get_due_challenges(self) -> list[dict]:
        """Вызовы с просроченным next_notify_at — для планировщика."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.*,
                    u.telegram_id,
                    COALESCE((
                        SELECT SUM(e.amount)
                        FROM expenses e
                        JOIN categories cat ON e.category_id = cat.category_id
                        WHERE e.user_id = c.user_id
                          AND cat.name = c.category_label
                          AND e.created_at::date BETWEEN c.period_start AND c.period_end
                    ), 0) AS spent_amount
                FROM challenges c
                JOIN users u ON c.user_id = u.user_id
                WHERE c.status = 'active'
                  AND c.next_notify_at <= NOW()
                  AND c.period_end >= NOW()::date
                """
            )
        return [_row_to_dict(r) for r in rows]

    async def get_expired_challenges(self) -> list[dict]:
        """Активные вызовы с истёкшим периодом — для подведения итогов."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.*,
                    u.telegram_id,
                    COALESCE((
                        SELECT SUM(e.amount)
                        FROM expenses e
                        JOIN categories cat ON e.category_id = cat.category_id
                        WHERE e.user_id = c.user_id
                          AND cat.name = c.category_label
                          AND e.created_at::date BETWEEN c.period_start AND c.period_end
                    ), 0) AS spent_amount
                FROM challenges c
                JOIN users u ON c.user_id = u.user_id
                WHERE c.status = 'active'
                  AND c.period_end < NOW()::date
                """
            )
        return [_row_to_dict(r) for r in rows]

    async def is_first_expense_this_month(self, telegram_id: int, category_label: str) -> bool:
        """True если в текущем месяце ровно 1 расход в этой категории (только что записанный)."""
        async with self.pool.acquire() as conn:
            cnt = await conn.fetchval(
                """
                SELECT COUNT(*) FROM expenses e
                JOIN categories cat ON e.category_id = cat.category_id
                WHERE e.user_id = (SELECT user_id FROM users WHERE telegram_id = $1)
                  AND cat.name = $2
                  AND DATE_TRUNC('month', e.created_at) = DATE_TRUNC('month', NOW())
                """,
                telegram_id, category_label,
            )
        return (cnt or 0) == 1

    async def count_spending_months(self, telegram_id: int, category_label: str) -> int:
        """Количество прошлых месяцев (до текущего) с тратами в категории за последние 6 мес."""
        async with self.pool.acquire() as conn:
            cnt = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT DATE_TRUNC('month', e.created_at))
                FROM expenses e
                JOIN categories cat ON e.category_id = cat.category_id
                WHERE e.user_id = (SELECT user_id FROM users WHERE telegram_id = $1)
                  AND cat.name = $2
                  AND e.created_at >= NOW() - INTERVAL '6 months'
                  AND DATE_TRUNC('month', e.created_at) < DATE_TRUNC('month', NOW())
                """,
                telegram_id, category_label,
            )
        return cnt or 0

    async def had_recent_failed_challenge(self, telegram_id: int) -> bool:
        """True если есть проваленный вызов за последние 60 дней (для достижения Железная воля)."""
        async with self.pool.acquire() as conn:
            cnt = await conn.fetchval(
                """
                SELECT COUNT(*) FROM challenges c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.telegram_id = $1
                  AND c.status = 'failed'
                  AND c.completed_at > NOW() - INTERVAL '60 days'
                """,
                telegram_id,
            )
        return (cnt or 0) > 0

    async def get_success_streak(self, telegram_id: int) -> int:
        """Количество успешных вызовов подряд (последние 10)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.status FROM challenges c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.telegram_id = $1
                  AND c.status IN ('success', 'failed')
                ORDER BY c.completed_at DESC
                LIMIT 10
                """,
                telegram_id,
            )
        streak = 0
        for r in rows:
            if r["status"] == "success":
                streak += 1
            else:
                break
        return streak

    async def get_user_id_by_telegram(self, telegram_id: int) -> int | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT user_id FROM users WHERE telegram_id = $1", telegram_id
            )

    # ── Обновление ────────────────────────────────────────────────────────────

    async def update_challenge_notify(
        self,
        challenge_id: int,
        notified_pct: int,
        next_notify_at: datetime,
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE challenges
                SET notified_pct = $1, next_notify_at = $2
                WHERE challenge_id = $3
                """,
                notified_pct, next_notify_at, challenge_id,
            )

    async def advance_notify(self, challenge_id: int) -> None:
        """Двигаем next_notify_at на завтра 10:00 если нечего отправлять."""
        nxt = (datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
               + timedelta(days=1))
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE challenges SET next_notify_at = $1 WHERE challenge_id = $2",
                nxt, challenge_id,
            )

    async def finalize_challenge(self, challenge_id: int, status: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE challenges
                SET status = $1, completed_at = NOW()
                WHERE challenge_id = $2
                """,
                status, challenge_id,
            )

    # ── Достижения ────────────────────────────────────────────────────────────

    async def get_all_achievements(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM achievements ORDER BY achievement_id"
            )
        return [dict(r) for r in rows]

    async def get_user_achievements_for_api(self, telegram_id: int) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.code, a.title, a.description, a.icon,
                       ua.earned_at, ua.challenge_id
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                JOIN users u ON ua.user_id = u.user_id
                WHERE u.telegram_id = $1
                ORDER BY ua.earned_at DESC
                """,
                telegram_id,
            )
        return [_row_to_dict(r) for r in rows]

    async def award_achievement(
        self,
        user_id: int,
        code: str,
        challenge_id: int | None,
    ) -> bool:
        """Выдаёт достижение. Возвращает True если выдано впервые."""
        async with self.pool.acquire() as conn:
            ach_id = await conn.fetchval(
                "SELECT achievement_id FROM achievements WHERE code = $1", code
            )
            if not ach_id:
                return False
            already = await conn.fetchval(
                "SELECT id FROM user_achievements WHERE user_id = $1 AND achievement_id = $2",
                user_id, ach_id,
            )
            if already:
                return False
            await conn.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_id, challenge_id)
                VALUES ($1, $2, $3)
                """,
                user_id, ach_id, challenge_id,
            )
        return True
