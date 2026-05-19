# services/notification_scheduler.py — фоновый планировщик уведомлений
import asyncio
import logging
from datetime import datetime, date, time as dtime, timedelta

from aiogram import Bot
from database import reminders as reminder_repo

logger = logging.getLogger(__name__)


def _calc_next_fire(interval: str, time_val, is_habit: bool, frequency: int = None) -> datetime | None:
    """
    Рассчитывает следующий момент отправки.
    interval — дата в формате "2025.01.01" для разовых напоминаний.
    time_val — объект datetime.time из PostgreSQL.
    Возвращает None, если время уже прошло и повтора нет.
    """
    now = datetime.now()

    if isinstance(time_val, dtime):
        fire_time = time_val
    else:
        parts = str(time_val).split(":")
        fire_time = dtime(int(parts[0]), int(parts[1]))

    if is_habit and frequency:
        candidate = datetime.combine(date.today(), fire_time)
        if candidate <= now:
            candidate += timedelta(days=frequency)
        return candidate

    try:
        fire_date = datetime.strptime(interval, "%Y.%m.%d").date()
    except ValueError:
        return None

    fire_dt = datetime.combine(fire_date, fire_time)
    return fire_dt if fire_dt > now else None


def initialize_next_fire_at() -> None:
    """Устанавливает next_fire_at для напоминаний без него (запускается при старте бота)."""
    rows = reminder_repo.get_reminders_without_next_fire()
    for reminder_id, is_habit, interval, time_val, frequency in rows:
        next_fire = _calc_next_fire(str(interval), time_val, bool(is_habit), frequency)
        if next_fire:
            reminder_repo.set_next_fire_at(reminder_id, next_fire)
            logger.info(f"Reminder {reminder_id}: next_fire_at = {next_fire}")
        else:
            logger.info(f"Reminder {reminder_id}: пропущено (время уже прошло)")


async def run_scheduler(bot: Bot) -> None:
    initialize_next_fire_at()
    logger.info("Notification scheduler started")

    while True:
        await asyncio.sleep(30)
        try:
            due = reminder_repo.get_due_reminders()
            for telegram_id, text, reminder_id, is_habit, frequency in due:
                try:
                    await bot.send_message(telegram_id, f"🔔 {text}")
                    reminder_repo.advance_next_fire(reminder_id, bool(is_habit), frequency)
                    logger.info(f"Sent reminder {reminder_id} → {telegram_id}")
                except Exception:
                    logger.exception(f"Failed to send reminder {reminder_id}")
        except Exception:
            logger.exception("Scheduler loop error")
