# database/reminder_repository.py — операции с напоминаниями и привычками
import logging
from datetime import date
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

    def create_reminder(self, name: str, text: str, telegram_id: int):
        self.db.execute(
            "SELECT recurrence_template_id FROM recurrence_templates "
            "WHERE name = %s ORDER BY recurrence_template_id DESC LIMIT 1",
            (name,)
        )
        template_id = self.db.fetchone()

        self.db.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
        user_id = self.db.fetchone()

        self.db.execute(
            "INSERT INTO reminders (user_id, recurrence_template_id, text) VALUES (%s, %s, %s)",
            (user_id, template_id, text)
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
