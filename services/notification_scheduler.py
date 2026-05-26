import asyncio
import logging

from aiogram import Bot
import database
from services.scheduler_utils import calc_next_fire, get_tz

logger = logging.getLogger(__name__)


async def initialize_next_fire_at() -> None:
    rows = await database.reminders.get_reminders_without_next_fire()
    for reminder_id, start_date, time_val, frequency, timezone_str in rows:
        tz = get_tz(timezone_str)
        next_fire = calc_next_fire("", time_val, is_habit=True, frequency=frequency, tz=tz)
        if next_fire:
            await database.reminders.set_next_fire_at(reminder_id, next_fire)
            logger.info(f"Habit {reminder_id}: next_fire_at = {next_fire}")
        else:
            logger.info(f"Habit {reminder_id}: пропущено")


async def run_scheduler(bot: Bot) -> None:
    await initialize_next_fire_at()
    logger.info("Notification scheduler started")

    while True:
        await asyncio.sleep(30)
        try:
            due = await database.reminders.get_due_reminders()
            for telegram_id, text, reminder_id, is_habit, frequency in due:
                try:
                    await bot.send_message(telegram_id, f"🔔 {text}")
                    await database.reminders.advance_next_fire(reminder_id, bool(is_habit), frequency)
                    logger.info(f"Sent reminder {reminder_id} → {telegram_id}")
                except Exception:
                    logger.exception(f"Failed to send reminder {reminder_id}")
        except Exception:
            logger.exception("Scheduler loop error")
