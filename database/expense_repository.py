# database/expense_repository.py — операции с расходами
import logging
from datetime import date
from database.db import PostgresConnection
from database.text_parser import split_text_and_amount

logger = logging.getLogger(__name__)


class ExpenseRepository:
    def __init__(self, db: PostgresConnection):
        self.db = db

    def save_voice_message(self, recognized_text: str, audio_data: str):
        """Сохраняет голосовое сообщение в БД."""
        self.db.execute(
            "INSERT INTO voice_message (recognized_text, audio_data) VALUES (%s, %s)",
            (recognized_text, audio_data)
        )
        self.db.commit()

    def save_expense(self, telegram_id: int, category: str, audio_data: str):
        """Сохраняет расход, привязывая голосовое сообщение к категории."""
        self.db.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
        user_id = self.db.fetchone()

        self.db.execute("SELECT category_id FROM categories WHERE name = %s", (category,))
        category_id = self.db.fetchone()

        self.db.execute(
            "SELECT voice_id, recognized_text FROM voice_message WHERE audio_data = %s",
            (audio_data,)
        )
        voice_row = self.db.fetchone()
        if not voice_row:
            raise ValueError(f"Voice message not found for audio: {audio_data}")

        voice_id, recognized_text = voice_row
        desc, amount, _ = split_text_and_amount(recognized_text)

        self.db.execute(
            "INSERT INTO expenses (user_id, category_id, voice_id, amount, description) "
            "VALUES (%s, %s, %s, %s, %s)",
            (user_id, category_id, voice_id, amount, desc)
        )
        self.db.commit()

    def get_expenses(self, telegram_id: int) -> list[tuple]:
        """Возвращает все расходы пользователя."""
        self.db.execute(
            """SELECT ex.amount, ex.description, ex.created_at, c.name
               FROM expenses ex
               JOIN users u ON ex.user_id = u.user_id
               LEFT JOIN categories c ON ex.category_id = c.category_id
               WHERE u.telegram_id = %s
               ORDER BY ex.created_at ASC""",
            (telegram_id,)
        )
        return self.db.fetchall()
