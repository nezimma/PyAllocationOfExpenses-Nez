# database/user_repository.py — операции с пользователями
import random
import logging
from database.db import PostgresConnection

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, db: PostgresConnection):
        self.db = db

    def register(self, telegram_id: int, login: str, password: str) -> bool:
        """Регистрирует нового пользователя. Возвращает True если создан, False если уже существует."""
        self.db.execute("SELECT username FROM users WHERE username = %s", (login,))
        if self.db.fetchall():
            logger.info(f"User {login} already exists")
            return False

        self.db.execute("SELECT COUNT(*) FROM managers")
        manager_count = self.db.fetchone()[0]
        manager_id = random.randint(1, max(manager_count, 1))

        self.db.execute(
            "INSERT INTO users (manager_id, telegram_id, username, password) VALUES (%s, %s, %s, %s)",
            (manager_id, telegram_id, login, password)
        )
        self.db.commit()
        logger.info(f"User {login} registered")
        return True

    def get_user_id(self, telegram_id: int) -> int | None:
        self.db.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
        row = self.db.fetchone()
        return row[0] if row else None
