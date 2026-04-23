# bot/__init__.py
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import config
from bot.routers import auth, expenses, reminders
from api.server import create_app

logger = logging.getLogger(__name__)


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=config.bot.token)
    dp = Dispatcher()
    dp.include_router(auth.router)
    dp.include_router(expenses.router)
    dp.include_router(reminders.router)
    return bot, dp


async def _start_api(port: int = 8080) -> web.AppRunner:
    runner = web.AppRunner(create_app())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info(f"API started on port {port}")
    return runner


async def run():
    logging.basicConfig(level=logging.INFO)
    bot, dp = create_bot()
    api_runner = await _start_api()
    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    finally:
        await api_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run())
