import logging
from datetime import date, datetime, time as dtime

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from bot.states import BotState
from bot.keyboards import reminders_menu, main_menu, reminder_actions_kb, habit_toggle_kb
import database
from services.scheduler_utils import calc_next_fire, get_tz

logger = logging.getLogger(__name__)
router = Router()

_MENU_COMMANDS = {"управлять напоминаниями", "на главное меню", "создать напоминание"}


@router.message(F.text.lower() == "напоминания")
async def menu_reminders(message: types.Message):
    await message.answer("Напоминания", reply_markup=reminders_menu())


@router.message(F.text.lower() == "на главное меню")
async def back_main(message: types.Message, state: FSMContext):
    await state.clear()
    from bot.keyboards import main_menu
    await message.answer("Главное меню", reply_markup=main_menu())


# ─── Создание напоминания ────────────────────────────────────────────────────

@router.message(F.text.lower() == "создать напоминание")
async def start_reminder(message: types.Message, state: FSMContext):
    await message.answer("Введите название напоминания")
    await state.set_state(BotState.callback_text_state)


@router.message(BotState.callback_text_state)
async def on_reminder_text(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст напоминания.")
        return
    if message.text.lower() in _MENU_COMMANDS:
        await state.clear()
        return await menu_reminders(message)
    await state.update_data(text=message.text)
    await message.answer(
        "📅 Введите дату напоминания\n"
        "Формат: ГГГГ.ММ.ДД\n"
        "Пример: 2026.12.31  (сначала год, потом месяц, потом день)"
    )
    await state.set_state(BotState.callback_date_state)


@router.message(BotState.callback_date_state)
async def on_reminder_date(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте дату текстом.")
        return
    if message.text.lower() in _MENU_COMMANDS:
        await state.clear()
        return await menu_reminders(message)

    try:
        parsed = datetime.strptime(message.text.strip(), "%Y.%m.%d")
        if parsed.date() < date.today():
            await message.answer(
                "⚠️ Эта дата уже прошла. Введите дату в будущем\n"
                "Формат: ГГГГ.ММ.ДД  (например: 2026.12.31)"
            )
            return
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты. Попробуйте ещё раз\n"
            "Формат: ГГГГ.ММ.ДД\n"
            "Пример: 2026.12.31  (сначала год, потом месяц, потом день)"
        )
        return

    await state.update_data(date=message.text.strip())
    await message.answer(
        "🕐 Введите время напоминания\n"
        "Формат: ЧЧ:ММ\n"
        "Пример: 09:00 или 21:30"
    )
    await state.set_state(BotState.callback_time_state)


@router.message(BotState.callback_time_state)
async def on_reminder_time(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте время текстом.")
        return
    if message.text.lower() in _MENU_COMMANDS:
        await state.clear()
        return await menu_reminders(message)

    try:
        h, m = map(int, message.text.strip().split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        fire_time = dtime(h, m)
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Неверный формат времени. Попробуйте ещё раз\n"
            "Формат: ЧЧ:ММ\n"
            "Пример: 09:00 или 21:30"
        )
        return

    data = await state.get_data()
    date_str = data["date"]
    time_str = message.text.strip()
    name = f"{time_str} {date_str}"

    try:
        await database.reminders.create_recurrence_template(name, 0, time_str)
        reminder_id = await database.reminders.create_reminder(name, data["text"], message.from_user.id)

        tz = get_tz(await database.users.get_timezone(message.from_user.id))
        next_fire = calc_next_fire(date_str, fire_time, is_habit=False, tz=tz)
        if next_fire:
            await database.reminders.set_next_fire_at(reminder_id, next_fire)

        await message.answer(
            f"✅ Напоминание создано!\n"
            f"📅 {date_str.replace('.', '/')}  🕐 {time_str}"
        )
    except Exception as e:
        logger.error(f"Ошибка создания напоминания: {e}")
        await message.answer("❌ Не удалось создать напоминание. Попробуйте ещё раз.")

    await state.clear()


# ─── Управление напоминаниями ────────────────────────────────────────────────

@router.message(F.text.lower() == "управлять напоминаниями")
async def manage_reminders(message: types.Message):
    rows = await database.reminders.get_reminders(message.from_user.id)
    if not rows:
        await message.answer("У вас нет напоминаний.")
        return

    for row in rows:
        text, is_habit, is_goal, next_fire_at, time, reminder_id, freq, start_date, active, habit_id = row
        if habit_id is not None:
            delta = date.today() - start_date
            days_left = delta.days % int(freq)
            next_str = f"{days_left} дн." if days_left != 0 else "Сегодня"
            status = "Активно" if active else "Не активно"
            await message.answer(
                f'🔁 Привычка «{text.capitalize()}»\n'
                f'Интервал: каждые {freq} дн.\n'
                f'Следующее: {next_str} в {str(time)[:5]}\n'
                f'Статус: {status}',
                reply_markup=habit_toggle_kb(habit_id),
            )
        else:
            date_display = next_fire_at.strftime("%d.%m.%Y") if next_fire_at else "—"
            await message.answer(
                f'🔔 Напоминание «{text.capitalize()}»\n'
                f'Дата: {date_display}\n'
                f'Время: {str(time)[:5]}',
                reply_markup=reminder_actions_kb(reminder_id),
            )


# ─── Callback handlers ───────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data.startswith("delete_"))
async def on_delete(cb: types.CallbackQuery):
    reminder_id = int(cb.data.split("_")[1])
    await database.reminders.delete_reminder(reminder_id)
    await cb.message.delete()


@router.callback_query(lambda c: c.data.startswith("aim_"))
async def on_create_goal(cb: types.CallbackQuery):
    reminder_id = int(cb.data.split("_")[1])
    # Конвертируем напоминание в цель через API Mini App (там уже есть полный UI).
    # В боте пока показываем подсказку.
    await cb.answer()
    await cb.message.answer(
        "🎯 Для создания цели откройте Mini App → вкладка «Напоминания» → "
        "нажмите на напоминание и выберите тип «Цель».\n\n"
        "Там можно задать дату начала, конца и интервал."
    )


@router.callback_query(lambda c: c.data.startswith("habit_"))
async def on_create_habit(cb: types.CallbackQuery, state: FSMContext):
    reminder_id = int(cb.data.split("_")[1])
    await cb.answer()
    await cb.message.answer("Введите интервал повторения в днях (например: 7)")
    await state.set_state(BotState.wait_habit_frequency)
    await state.update_data(number_reminder=reminder_id)


@router.message(BotState.wait_habit_frequency)
async def on_habit_frequency(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте число дней текстом.")
        return
    try:
        frequency = int(message.text.strip())
        if frequency <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введите целое число дней — например, 1, 7 или 30\n"
            "Попробуйте ещё раз:"
        )
        return

    data = await state.get_data()
    reminder_id = data["number_reminder"]
    await database.reminders.create_habit(reminder_id, frequency)

    row = await database.reminders.get_reminder_time(reminder_id)
    if row:
        interval, time_val = row
        tz = get_tz(await database.users.get_timezone(message.from_user.id))
        next_fire = calc_next_fire(str(interval), time_val, is_habit=True, frequency=frequency, tz=tz)
        if next_fire:
            await database.reminders.set_next_fire_at(reminder_id, next_fire)

    await message.answer("✅ Привычка создана")
    await state.clear()


@router.callback_query(lambda c: c.data.startswith("activate_"))
async def on_toggle_habit(cb: types.CallbackQuery):
    habit_id = int(cb.data.split("_")[1])
    row = await database.reminders.toggle_habit(habit_id)
    delta = date.today() - row[3]
    days_left = delta.days % int(row[2])
    next_str = f"{days_left} дн." if days_left != 0 else "Сегодня"
    status = "Активно" if row[4] else "Не активно"
    await cb.message.edit_text(
        f'🔁 Привычка «{row[5].capitalize()}»\n'
        f'Интервал: каждые {row[2]} дн.\n'
        f'Следующее: {next_str} в {str(row[6])[:5]}\n'
        f'Статус: {status}',
        reply_markup=habit_toggle_kb(row[0]),
    )
