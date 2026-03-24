# bot/__init__.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import config
from bot.routers import auth, expenses, reminders

logger = logging.getLogger(__name__)


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=config.bot.token)
    dp = Dispatcher()
    dp.include_router(auth.router)
    dp.include_router(expenses.router)
    dp.include_router(reminders.router)
    return bot, dp


async def run():
    logging.basicConfig(level=logging.INFO)
    bot, dp = create_bot()
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
