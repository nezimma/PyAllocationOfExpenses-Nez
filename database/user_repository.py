import random
import logging
import asyncpg

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def register(self, telegram_id: int, login: str, password: str) -> bool:
        """Регистрирует нового пользователя. Возвращает True если создан, False если уже существует."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT username FROM users WHERE username = $1", login)
            if row:
                logger.info(f"User {login} already exists")
                return False

            manager_count = await conn.fetchval("SELECT COUNT(*) FROM managers") or 0
            manager_id = random.randint(1, max(int(manager_count), 1))

            await conn.execute(
                "INSERT INTO users (manager_id, telegram_id, username, password) VALUES ($1, $2, $3, $4)",
                manager_id, telegram_id, login, password,
            )
            logger.info(f"User {login} registered")
            return True

    async def get_user_id(self, telegram_id: int) -> int | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT user_id FROM users WHERE telegram_id = $1", telegram_id)

    async def get_timezone(self, telegram_id: int) -> str | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT timezone FROM users WHERE telegram_id = $1", telegram_id)

    async def set_timezone(self, telegram_id: int, timezone_str: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET timezone = $1 WHERE telegram_id = $2",
                timezone_str, telegram_id,
            )
