import logging
from datetime import date, datetime, time as dtime
import asyncpg

logger = logging.getLogger(__name__)


def _parse_time(value) -> dtime:
    """'09:00' или '9:00' или уже datetime.time → datetime.time."""
    if isinstance(value, dtime):
        return value
    h, m = map(int, str(value).strip().split(":"))
    return dtime(h, m)


def _parse_date(value) -> date:
    """'2026-05-21' или '2026.05.21' или уже datetime.date → datetime.date."""
    if isinstance(value, date):
        return value
    s = str(value).strip().replace(".", "-")
    return datetime.strptime(s, "%Y-%m-%d").date()


class ReminderRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_recurrence_template(self, name: str, interval: int, time):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO recurrence_templates (name, interval, time) VALUES ($1, $2, $3)",
                name, interval, _parse_time(time),
            )

    async def create_reminder(self, name: str, text: str, telegram_id: int) -> int:
        async with self.pool.acquire() as conn:
            template_id = await conn.fetchval(
                "SELECT recurrence_template_id FROM recurrence_templates "
                "WHERE name = $1 ORDER BY recurrence_template_id DESC LIMIT 1",
                name,
            )
            user_id = await conn.fetchval(
                "SELECT user_id FROM users WHERE telegram_id = $1", telegram_id
            )
            return await conn.fetchval(
                "INSERT INTO reminders (user_id, recurrence_template_id, text) VALUES ($1, $2, $3) RETURNING reminder_id",
                user_id, template_id, text,
            )

    async def set_next_fire_at(self, reminder_id: int, next_fire_at: datetime):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE reminders SET next_fire_at = $1 WHERE reminder_id = $2",
                next_fire_at, reminder_id,
            )

    async def get_reminders_without_next_fire(self) -> list[tuple]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT r.reminder_id, h.start_date, rt.time, h.frequency,
                          COALESCE(u.timezone, 'Europe/Minsk') AS timezone
                   FROM reminders r
                   JOIN users u ON r.user_id = u.user_id
                   JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
                   JOIN habits h ON r.reminder_id = h.reminder_id
                   WHERE r.next_fire_at IS NULL AND r.is_habit = true AND h.active = true""",
            )
            return [tuple(r) for r in rows]

    async def get_reminder_time(self, reminder_id: int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT rt.interval, rt.time FROM reminders r
                   JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
                   WHERE r.reminder_id = $1""",
                reminder_id,
            )
            return tuple(row) if row else None

    async def get_due_reminders(self) -> list[tuple]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT u.telegram_id, r.text, r.reminder_id, r.is_habit, h.frequency
                   FROM reminders r
                   JOIN users u ON r.user_id = u.user_id
                   LEFT JOIN habits h ON r.reminder_id = h.reminder_id AND r.is_habit = true
                   WHERE r.next_fire_at <= NOW()
                     AND r.next_fire_at IS NOT NULL
                     AND (r.is_habit = false OR h.active = true)""",
            )
            return [tuple(r) for r in rows]

    async def advance_next_fire(self, reminder_id: int, is_habit: bool, frequency: int = None):
        async with self.pool.acquire() as conn:
            if is_habit and frequency:
                await conn.execute(
                    "UPDATE reminders SET next_fire_at = next_fire_at + ($1 || ' days')::INTERVAL WHERE reminder_id = $2",
                    str(frequency), reminder_id,
                )
            else:
                await conn.execute(
                    "UPDATE reminders SET next_fire_at = NULL WHERE reminder_id = $1",
                    reminder_id,
                )

    async def get_reminders(self, telegram_id: int) -> list[tuple]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT r.text, r.is_habit, r.is_goal, r.next_fire_at, rt.time,
                          r.reminder_id, h.frequency, h.start_date, h.active, h.habit_id
                   FROM reminders r
                   JOIN users u ON r.user_id = u.user_id
                   JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
                   LEFT JOIN habits h ON r.reminder_id = h.reminder_id AND r.is_habit = true
                   WHERE u.telegram_id = $1
                   ORDER BY r.reminder_id ASC""",
                telegram_id,
            )
            return [tuple(r) for r in rows]

    async def get_telegram_id_by_reminder(self, reminder_id: int) -> int | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT u.telegram_id FROM reminders r JOIN users u ON r.user_id = u.user_id WHERE r.reminder_id = $1",
                reminder_id,
            )

    async def delete_reminder(self, reminder_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM reminders WHERE reminder_id = $1", reminder_id)

    async def create_habit(self, reminder_id: int, frequency: int):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO habits (reminder_id, frequency, start_date, active) VALUES ($1, $2, $3, $4)",
                    reminder_id, frequency, date.today(), True,
                )
                await conn.execute(
                    "UPDATE reminders SET is_habit = True WHERE reminder_id = $1", reminder_id
                )

    # ── API методы (Mini App) ──────────────────────────────────────────────────

    async def get_reminders_for_api(self, telegram_id: int) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT r.reminder_id, r.is_habit, r.is_goal, r.text,
                          r.next_fire_at, rt.time,
                          h.habit_id, h.frequency, h.start_date AS h_start, h.active,
                          g.goal_id, g.start_date AS g_start, g.end_date
                   FROM reminders r
                   JOIN users u ON r.user_id = u.user_id
                   JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
                   LEFT JOIN habits h ON r.reminder_id = h.reminder_id AND r.is_habit = true
                   LEFT JOIN goals  g ON r.reminder_id = g.reminder_id  AND r.is_goal  = true
                   WHERE u.telegram_id = $1
                   ORDER BY r.reminder_id ASC""",
                telegram_id,
            )
            if not rows:
                return []

            reminder_ids = [r["reminder_id"] for r in rows]
            checkin_rows = await conn.fetch(
                "SELECT reminder_id, checkin_date FROM checkins WHERE reminder_id = ANY($1::int[]) ORDER BY checkin_date",
                reminder_ids,
            )

        checkins_map: dict[int, list[str]] = {}
        for cr in checkin_rows:
            checkins_map.setdefault(cr["reminder_id"], []).append(cr["checkin_date"].isoformat())

        result = []
        for row in rows:
            rid      = row["reminder_id"]
            is_habit = row["is_habit"]
            is_goal  = row["is_goal"]
            h_start  = row["h_start"]
            g_start  = row["g_start"]
            g_end    = row["end_date"]
            frequency = row["frequency"]
            time_val  = row["time"]
            h_active  = row["active"]
            next_fire_at = row["next_fire_at"]

            rtype = "habit" if is_habit else ("goal" if is_goal else "reminder")

            if is_habit and h_start:
                date_str = h_start.isoformat()
            elif is_goal and g_start:
                date_str = g_start.isoformat()
            elif next_fire_at:
                date_str = next_fire_at.date().isoformat()
            else:
                date_str = ""

            d = {
                "id":       rid,
                "type":     rtype,
                "title":    row["text"],
                "date":     date_str,
                "time":     str(time_val)[:5],
                "active":   bool(h_active) if is_habit else True,
                "checkins": checkins_map.get(rid, []),
            }
            if is_habit and frequency is not None:
                d["interval"] = int(frequency)
            if is_goal:
                d["endDate"]  = g_end.isoformat() if g_end else None
                d["interval"] = int(frequency) if frequency else 1
            result.append(d)
        return result

    async def create_reminder_full(
        self, telegram_id: int, title: str, date_str: str,
        time_str: str, rtype: str, interval: int, end_date: str | None,
    ) -> int:
        interval_days = interval if rtype != "reminder" else 0
        name = f"{time_str} {date_str}"
        is_habit = rtype == "habit"
        is_goal  = rtype == "goal"

        parsed_time = _parse_time(time_str)
        parsed_date = _parse_date(date_str)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                template_id = await conn.fetchval(
                    "INSERT INTO recurrence_templates (name, interval, time) VALUES ($1, $2, $3) RETURNING recurrence_template_id",
                    name, interval_days, parsed_time,
                )
                user_id = await conn.fetchval(
                    "SELECT user_id FROM users WHERE telegram_id = $1", telegram_id
                )
                reminder_id = await conn.fetchval(
                    "INSERT INTO reminders (user_id, recurrence_template_id, text, is_habit, is_goal) "
                    "VALUES ($1, $2, $3, $4, $5) RETURNING reminder_id",
                    user_id, template_id, title, is_habit, is_goal,
                )
                if is_habit:
                    await conn.execute(
                        "INSERT INTO habits (reminder_id, frequency, start_date, active) VALUES ($1, $2, $3, true)",
                        reminder_id, interval or 1, parsed_date,
                    )
                elif is_goal:
                    parsed_end = _parse_date(end_date) if end_date else None
                    await conn.execute(
                        "INSERT INTO goals (reminder_id, description, start_date, end_date) VALUES ($1, $2, $3, $4)",
                        reminder_id, title, parsed_date, parsed_end,
                    )
        return reminder_id

    async def update_reminder_full(
        self, reminder_id: int, title: str, date_str: str,
        time_str: str, rtype: str, interval: int, end_date: str | None,
    ) -> None:
        interval_days = interval if rtype != "reminder" else 0
        name = f"{time_str} {date_str}"
        is_habit = rtype == "habit"
        is_goal  = rtype == "goal"

        parsed_time = _parse_time(time_str)
        parsed_date = _parse_date(date_str)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """UPDATE recurrence_templates SET name = $1, interval = $2, time = $3
                       WHERE recurrence_template_id = (
                           SELECT recurrence_template_id FROM reminders WHERE reminder_id = $4
                       )""",
                    name, interval_days, parsed_time, reminder_id,
                )
                await conn.execute(
                    "UPDATE reminders SET text = $1, is_habit = $2, is_goal = $3 WHERE reminder_id = $4",
                    title, is_habit, is_goal, reminder_id,
                )
                await conn.execute("DELETE FROM habits WHERE reminder_id = $1", reminder_id)
                await conn.execute("DELETE FROM goals  WHERE reminder_id = $1", reminder_id)

                if is_habit:
                    await conn.execute(
                        "INSERT INTO habits (reminder_id, frequency, start_date, active) VALUES ($1, $2, $3, true)",
                        reminder_id, interval or 1, parsed_date,
                    )
                elif is_goal:
                    parsed_end = _parse_date(end_date) if end_date else None
                    await conn.execute(
                        "INSERT INTO goals (reminder_id, description, start_date, end_date) VALUES ($1, $2, $3, $4)",
                        reminder_id, title, parsed_date, parsed_end,
                    )

    async def toggle_reminder_active(self, reminder_id: int) -> bool:
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "UPDATE habits SET active = NOT active WHERE reminder_id = $1 RETURNING active",
                reminder_id,
            )
            return bool(val) if val is not None else True

    async def toggle_habit(self, habit_id: int) -> tuple:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE habits SET active = NOT active WHERE habit_id = $1", habit_id
            )
            row = await conn.fetchrow(
                """SELECT h.*, r.text, rt.time FROM habits h
                   JOIN reminders r ON r.reminder_id = h.reminder_id
                   JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
                   WHERE habit_id = $1""",
                habit_id,
            )
            return tuple(row) if row else None

    async def add_checkin(self, reminder_id: int, checkin_date: str) -> bool:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO checkins (reminder_id, checkin_date) VALUES ($1, $2)",
                    reminder_id, checkin_date,
                )
                return True
            except asyncpg.UniqueViolationError:
                return False
