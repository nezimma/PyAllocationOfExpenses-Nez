from datetime import datetime, date, time as dtime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def calc_next_fire(
    date_str: str,
    time_val: dtime | str,
    is_habit: bool,
    frequency: int = None,
    tz: ZoneInfo = None,
) -> datetime | None:
    """
    Рассчитывает следующий момент отправки с учётом часового пояса.

    date_str   — дата в формате "2025.01.01" для разовых напоминаний.
    time_val   — объект datetime.time или строка "HH:MM".
    tz         — часовой пояс пользователя; если None, используется местное время сервера.
    Возвращает None, если время уже прошло и повтора нет.
    """
    if isinstance(time_val, str):
        parts = time_val.split(":")
        fire_time = dtime(int(parts[0]), int(parts[1]))
    else:
        fire_time = time_val

    now = datetime.now(tz=tz)

    if is_habit and frequency:
        today = now.date()
        candidate = datetime(today.year, today.month, today.day,
                             fire_time.hour, fire_time.minute, tzinfo=tz)
        if candidate <= now:
            candidate += timedelta(days=frequency)
        return candidate

    try:
        fire_date = datetime.strptime(date_str, "%Y.%m.%d").date()
    except ValueError:
        return None

    fire_dt = datetime(fire_date.year, fire_date.month, fire_date.day,
                       fire_time.hour, fire_time.minute, tzinfo=tz)
    return fire_dt if fire_dt > now else None


def get_tz(timezone_str: str | None) -> ZoneInfo | None:
    """Возвращает ZoneInfo по строке. None если строка пустая или невалидная."""
    if not timezone_str:
        return None
    try:
        return ZoneInfo(timezone_str)
    except (ZoneInfoNotFoundError, KeyError):
        return None
