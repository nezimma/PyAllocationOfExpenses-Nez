import asyncpg


async def create_pool(host: str, user: str, password: str, db_name: str, port: int = 5432) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=host, user=user, password=password,
        database=db_name, port=port,
        min_size=2, max_size=10,
    )
