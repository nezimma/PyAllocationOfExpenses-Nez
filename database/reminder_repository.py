# database/reminder_repository.py — операции с напоминаниями и привычками
import logging
from datetime import date, datetime
from database.db import PostgresConnection

logger = logging.getLogger(__name__)


class ReminderRepository:
    def __init__(self, db: PostgresConnection):
        self.db = db

    def create_recurrence_template(self, name: str, interval: str, time: str):
        self.db.execute(
            "INSERT INTO recurrence_templates (name, interval, time) VALUES (%s, %s, %s)",
            (name, interval, time)
        )
        self.db.commit()

    def create_reminder(self, name: str, text: str, telegram_id: int) -> int:
        self.db.execute(
            "SELECT recurrence_template_id FROM recurrence_templates "
            "WHERE name = %s ORDER BY recurrence_template_id DESC LIMIT 1",
            (name,)
        )
        template_id = self.db.fetchone()

        self.db.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
        user_id = self.db.fetchone()

        self.db.execute(
            "INSERT INTO reminders (user_id, recurrence_template_id, text) VALUES (%s, %s, %s) RETURNING reminder_id",
            (user_id, template_id, text)
        )
        reminder_id = self.db.fetchone()[0]
        self.db.commit()
        return reminder_id

    def set_next_fire_at(self, reminder_id: int, next_fire_at: datetime):
        self.db.execute(
            "UPDATE reminders SET next_fire_at = %s WHERE reminder_id = %s",
            (next_fire_at, reminder_id)
        )
        self.db.commit()

    def get_reminders_without_next_fire(self) -> list[tuple]:
        """Возвращает напоминания без рассчитанного next_fire_at для инициализации при старте."""
        self.db.execute(
            """SELECT r.reminder_id, r.is_habit, rt.interval, rt.time, h.frequency
               FROM reminders r
               JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
               LEFT JOIN habits h ON r.reminder_id = h.reminder_id AND r.is_habit = true
               WHERE r.next_fire_at IS NULL""",
        )
        return self.db.fetchall()

    def get_reminder_time(self, reminder_id: int):
        """Возвращает (interval, time) из шаблона для нужного напоминания."""
        self.db.execute(
            """SELECT rt.interval, rt.time FROM reminders r
               JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
               WHERE r.reminder_id = %s""",
            (reminder_id,)
        )
        return self.db.fetchone()

    def get_due_reminders(self) -> list[tuple]:
        """Возвращает напоминания, время которых наступило."""
        self.db.execute(
            """SELECT u.telegram_id, r.text, r.reminder_id, r.is_habit, h.frequency
               FROM reminders r
               JOIN users u ON r.user_id = u.user_id
               LEFT JOIN habits h ON r.reminder_id = h.reminder_id AND r.is_habit = true
               WHERE r.next_fire_at <= NOW()
                 AND r.next_fire_at IS NOT NULL
                 AND (r.is_habit = false OR h.active = true)"""
        )
        return self.db.fetchall()

    def advance_next_fire(self, reminder_id: int, is_habit: bool, frequency: int = None):
        """После отправки: для привычки сдвигаем на следующий период, для разового — сбрасываем."""
        if is_habit and frequency:
            self.db.execute(
                "UPDATE reminders SET next_fire_at = next_fire_at + (%s || ' days')::INTERVAL WHERE reminder_id = %s",
                (str(frequency), reminder_id)
            )
        else:
            self.db.execute(
                "UPDATE reminders SET next_fire_at = NULL WHERE reminder_id = %s",
                (reminder_id,)
            )
        self.db.commit()

    def get_reminders(self, telegram_id: int) -> list[tuple]:
        self.db.execute(
            """SELECT r.text, r.is_habit, r.is_goal, rt.interval, rt.time,
                      r.reminder_id, h.frequency, h.start_date, h.active, h.habit_id
               FROM reminders r
               JOIN users u ON r.user_id = u.user_id
               JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
               LEFT JOIN habits h ON r.reminder_id = h.reminder_id AND r.is_habit = true
               WHERE u.telegram_id = %s
               ORDER BY r.reminder_id ASC""",
            (telegram_id,)
        )
        return self.db.fetchall()

    def delete_reminder(self, reminder_id: int):
        self.db.execute("DELETE FROM reminders WHERE reminder_id = %s", (reminder_id,))
        self.db.commit()

    def create_habit(self, reminder_id: int, frequency: int):
        today = date.today()
        self.db.execute(
            "INSERT INTO habits (reminder_id, frequency, start_date, active) VALUES (%s, %s, %s, %s)",
            (reminder_id, frequency, today, True)
        )
        self.db.execute(
            "UPDATE reminders SET is_habit = True WHERE reminder_id = %s",
            (reminder_id,)
        )
        self.db.commit()

    # ── API методы (Mini App) ──────────────────────────────────────────────────

    def get_reminders_for_api(self, telegram_id: int) -> list[dict]:
        self.db.execute(
            """SELECT r.reminder_id, r.is_habit, r.is_goal, r.text,
                      rt.interval, rt.time,
                      h.habit_id, h.frequency, h.start_date, h.active,
                      g.goal_id, g.start_date, g.end_date
               FROM reminders r
               JOIN users u ON r.user_id = u.user_id
               JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
               LEFT JOIN habits h ON r.reminder_id = h.reminder_id AND r.is_habit = true
               LEFT JOIN goals  g ON r.reminder_id = g.reminder_id  AND r.is_goal  = true
               WHERE u.telegram_id = %s
               ORDER BY r.reminder_id ASC""",
            (telegram_id,)
        )
        rows = self.db.fetchall()
        result = []
        for row in rows:
            (rid, is_habit, is_goal, text, interval, time_val,
             habit_id, frequency, h_start, h_active,
             goal_id, g_start, g_end) = row

            rtype = 'habit' if is_habit else ('goal' if is_goal else 'reminder')

            # interval хранится как "2025.01.01" → конвертируем в "2025-01-01"
            date_str = str(interval).replace('.', '-') if interval else ''

            d = {
                'id':     rid,
                'type':   rtype,
                'title':  text,
                'date':   date_str,
                'time':   str(time_val)[:5],
                'active': bool(h_active) if is_habit else True,
                'checkins': [],
            }
            if is_habit and frequency is not None:
                d['interval'] = int(frequency)
            if is_goal:
                d['endDate']  = g_end.isoformat() if g_end else None
                d['interval'] = int(frequency) if frequency else 1
            result.append(d)
        return result

    def create_reminder_full(
        self, telegram_id: int, title: str, date_str: str,
        time_str: str, rtype: str, interval: int, end_date: str | None
    ) -> int:
        """Создаёт шаблон + напоминание + запись привычки/цели. Возвращает reminder_id."""
        # date_str приходит как "2025-01-01" → храним как "2025.01.01"
        interval_stored = date_str.replace('-', '.')
        name = f"{time_str} {interval_stored}"

        self.db.execute(
            "INSERT INTO recurrence_templates (name, interval, time) VALUES (%s, %s, %s) RETURNING recurrence_template_id",
            (name, interval_stored, time_str)
        )
        template_id = self.db.fetchone()[0]

        self.db.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
        user_id = self.db.fetchone()[0]

        is_habit = rtype == 'habit'
        is_goal  = rtype == 'goal'
        self.db.execute(
            "INSERT INTO reminders (user_id, recurrence_template_id, text, is_habit, is_goal) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING reminder_id",
            (user_id, template_id, title, is_habit, is_goal)
        )
        reminder_id = self.db.fetchone()[0]

        start = date_str  # "2025-01-01"
        if is_habit:
            self.db.execute(
                "INSERT INTO habits (reminder_id, frequency, start_date, active) VALUES (%s, %s, %s, true)",
                (reminder_id, interval or 1, start)
            )
        elif is_goal:
            self.db.execute(
                "INSERT INTO goals (reminder_id, description, start_date, end_date) VALUES (%s, %s, %s, %s)",
                (reminder_id, title, start, end_date)
            )

        self.db.commit()
        return reminder_id

    def update_reminder_full(
        self, reminder_id: int, title: str, date_str: str,
        time_str: str, rtype: str, interval: int, end_date: str | None
    ) -> None:
        interval_stored = date_str.replace('-', '.')
        name = f"{time_str} {interval_stored}"

        # Обновляем шаблон
        self.db.execute(
            """UPDATE recurrence_templates SET name = %s, interval = %s, time = %s
               WHERE recurrence_template_id = (
                   SELECT recurrence_template_id FROM reminders WHERE reminder_id = %s
               )""",
            (name, interval_stored, time_str, reminder_id)
        )

        is_habit = rtype == 'habit'
        is_goal  = rtype == 'goal'
        self.db.execute(
            "UPDATE reminders SET text = %s, is_habit = %s, is_goal = %s WHERE reminder_id = %s",
            (title, is_habit, is_goal, reminder_id)
        )

        # Удаляем старые habit/goal и пересоздаём нужные
        self.db.execute("DELETE FROM habits WHERE reminder_id = %s", (reminder_id,))
        self.db.execute("DELETE FROM goals  WHERE reminder_id = %s", (reminder_id,))

        if is_habit:
            self.db.execute(
                "INSERT INTO habits (reminder_id, frequency, start_date, active) VALUES (%s, %s, %s, true)",
                (reminder_id, interval or 1, date_str)
            )
        elif is_goal:
            self.db.execute(
                "INSERT INTO goals (reminder_id, description, start_date, end_date) VALUES (%s, %s, %s, %s)",
                (reminder_id, title, date_str, end_date)
            )

        self.db.commit()

    def toggle_reminder_active(self, reminder_id: int) -> bool:
        """Переключает active у привычки. Возвращает новое значение."""
        self.db.execute(
            "UPDATE habits SET active = NOT active WHERE reminder_id = %s RETURNING active",
            (reminder_id,)
        )
        row = self.db.fetchone()
        self.db.commit()
        return bool(row[0]) if row else True

    def toggle_habit(self, habit_id: int) -> tuple:
        self.db.execute("UPDATE habits SET active = NOT active WHERE habit_id = %s", (habit_id,))
        self.db.commit()
        self.db.execute(
            """SELECT h.*, r.text, rt.time FROM habits h
               JOIN reminders r ON r.reminder_id = h.reminder_id
               JOIN recurrence_templates rt ON r.recurrence_template_id = rt.recurrence_template_id
               WHERE habit_id = %s""",
            (habit_id,)
        )
        return self.db.fetchone()
