# database/model_repository.py — хранение метаданных ML-моделей
import logging
from database.db import PostgresConnection

logger = logging.getLogger(__name__)


class ModelRepository:
    def __init__(self, db: PostgresConnection):
        self.db = db

    def init_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                file_path TEXT NOT NULL,
                version INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.commit()

    def save_metadata(self, name: str, file_path: str, version: int):
        self.db.execute(
            "INSERT INTO models (name, file_path, version) VALUES (%s, %s, %s)",
            (name, file_path, version)
        )
        self.db.commit()

    def get_latest(self, name: str) -> tuple | None:
        self.db.execute(
            "SELECT file_path, version FROM models WHERE name = %s ORDER BY version DESC LIMIT 1",
            (name,)
        )
        return self.db.fetchone()
