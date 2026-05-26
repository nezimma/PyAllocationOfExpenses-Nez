import logging
import asyncpg
from database.text_parser import split_text_and_amount

logger = logging.getLogger(__name__)

_CATEGORY_ALIASES: dict[str, str] = {
    "Ресторан и еда": "Рестораны и еда",
}

_CATEGORY_TO_KEY: dict[str, str] = {
    "Рестораны и еда": "restaurants",
    "Транспорт":       "transport",
    "Жилье":           "housing",
    "Одежда":          "clothes",
    "Быт":             "household",
    "Техника":         "tech",
}


def _normalize_category(name: str) -> str:
    return _CATEGORY_ALIASES.get(name, name)


class ExpenseRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def save_voice_message(self, recognized_text: str, audio_data: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO voice_message (recognized_text, audio_data) VALUES ($1, $2)",
                recognized_text, audio_data,
            )

    async def save_expense(self, telegram_id: int, category: str, audio_data: str):
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval(
                "SELECT user_id FROM users WHERE telegram_id = $1", telegram_id
            )
            voice_row = await conn.fetchrow(
                "SELECT voice_id, recognized_text FROM voice_message WHERE audio_data = $1", audio_data
            )
            if not voice_row:
                raise ValueError(f"Voice message not found for audio: {audio_data}")

            desc, amount, _ = split_text_and_amount(voice_row["recognized_text"])
            category = _normalize_category(category)
            category_id = await conn.fetchval(
                "SELECT category_id FROM categories WHERE name = $1", category
            )
            await conn.execute(
                "INSERT INTO expenses (user_id, category_id, voice_id, amount, description) "
                "VALUES ($1, $2, $3, $4, $5)",
                user_id, category_id, voice_row["voice_id"], amount, desc,
            )

    async def save_expense_items(
        self,
        telegram_id: int,
        items: list[tuple[str, str, float | None]],
        audio_data: str,
    ):
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval(
                "SELECT user_id FROM users WHERE telegram_id = $1", telegram_id
            )
            voice_row = await conn.fetchrow(
                "SELECT voice_id FROM voice_message WHERE audio_data = $1", audio_data
            )
            if not voice_row:
                raise ValueError(f"Voice message not found for audio: {audio_data}")
            voice_id = voice_row["voice_id"]

            async with conn.transaction():
                for category, desc, amount in items:
                    category = _normalize_category(category)
                    category_id = await conn.fetchval(
                        "SELECT category_id FROM categories WHERE name = $1", category
                    )
                    await conn.execute(
                        "INSERT INTO expenses (user_id, category_id, voice_id, amount, description) "
                        "VALUES ($1, $2, $3, $4, $5)",
                        user_id, category_id, voice_id, amount, desc,
                    )

    async def get_expenses(self, telegram_id: int) -> list[tuple]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT ex.amount, ex.description, ex.created_at, c.name
                   FROM expenses ex
                   JOIN users u ON ex.user_id = u.user_id
                   LEFT JOIN categories c ON ex.category_id = c.category_id
                   WHERE u.telegram_id = $1
                   ORDER BY ex.created_at ASC""",
                telegram_id,
            )
            return [tuple(r) for r in rows]

    async def get_expenses_for_api(self, telegram_id: int) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT ex.description, c.name, ex.amount, ex.created_at
                   FROM expenses ex
                   JOIN users u ON ex.user_id = u.user_id
                   LEFT JOIN categories c ON ex.category_id = c.category_id
                   WHERE u.telegram_id = $1
                   ORDER BY ex.created_at DESC""",
                telegram_id,
            )
            return [
                {
                    "id":     i + 1,
                    "name":   row["description"] or "",
                    "cat":    _CATEGORY_TO_KEY.get(row["name"], "other"),
                    "amount": float(row["amount"]) if row["amount"] else 0.0,
                    "date":   row["created_at"].isoformat() if row["created_at"] else None,
                }
                for i, row in enumerate(rows)
            ]
