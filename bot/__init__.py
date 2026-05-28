import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import config
from bot.routers import auth, expenses, reminders, challenges, pet
from api.server import create_app
from services.notification_scheduler import run_scheduler
from database.db import create_pool
import database
import ml
from ml.file_model_repository import FileModelRepository

logger = logging.getLogger(__name__)


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=config.bot.token)
    dp = Dispatcher()
    dp.include_router(auth.router)
    dp.include_router(expenses.router)
    dp.include_router(reminders.router)
    dp.include_router(challenges.router)
    dp.include_router(pet.router)
    return bot, dp


async def _start_api(port: int = 8080) -> web.AppRunner:
    runner = web.AppRunner(create_app())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info(f"API started on port {port}")
    return runner


async def run():
    logging.basicConfig(level=logging.INFO)

    pool = await create_pool(
        host=config.database.host,
        user=config.database.user,
        password=config.database.password,
        db_name=config.database.db_name,
        port=config.database.port,
    )
    database.init(pool)
    logger.info("DB pool initialized")

    # Инициализируем ML-сервис (метаданные модели читаются из файла, не из БД)
    model_repo = FileModelRepository(models_dir=config.model.dir)
    ml.init_model_svc(model_repo)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, ml.model_svc.load_latest)
    logger.info("ML model loaded")

    bot, dp = create_bot()
    api_runner = await _start_api()
    try:
        logger.info("Bot started")
        asyncio.create_task(run_scheduler(bot))
        await dp.start_polling(bot)
    finally:
        await api_runner.cleanup()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run())
