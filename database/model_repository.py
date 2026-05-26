import logging
import asyncpg

logger = logging.getLogger(__name__)


class ModelRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def init_table(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),
                    file_path TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def save_metadata(self, name: str, file_path: str, version: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO models (name, file_path, version) VALUES ($1, $2, $3)",
                name, file_path, version,
            )

    async def get_latest(self, name: str) -> tuple | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT file_path, version FROM models WHERE name = $1 ORDER BY version DESC LIMIT 1",
                name,
            )
            return tuple(row) if row else None
