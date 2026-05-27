"""Запускает SQL-миграцию через asyncpg."""
import asyncio
import sys
from config import config
from database.db import create_pool


async def main(sql_file: str):
    with open(sql_file, encoding="utf-8") as f:
        sql = f.read()

    pool = await create_pool(
        host=config.database.host,
        user=config.database.user,
        password=config.database.password,
        db_name=config.database.db_name,
        port=config.database.port,
    )
    async with pool.acquire() as conn:
        await conn.execute(sql)
    await pool.close()
    print(f"Migration applied: {sql_file}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "migrations/add_currency.sql"
    asyncio.run(main(path))
