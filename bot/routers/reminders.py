# bot/routers/reminders.py — создание напоминаний и управление привычками
import logging
from datetime import date

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from bot.states import BotState
from bot.keyboards import reminders_menu, main_menu, reminder_actions_kb, habit_toggle_kb
from database import reminders as reminder_repo

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
    if message.text.lower() in _MENU_COMMANDS:
        await state.clear()
        return await menu_reminders(message)
    await state.update_data(text=message.text)
    await message.answer("Введите дату в формате 2025.01.01")
    await state.set_state(BotState.callback_date_state)


@router.message(BotState.callback_date_state)
async def on_reminder_date(message: types.Message, state: FSMContext):
    if message.text.lower() in _MENU_COMMANDS:
        await state.clear()
        return await menu_reminders(message)
    await state.update_data(date=message.text)
    await message.answer("Введите время в формате 12:00")
    await state.set_state(BotState.callback_time_state)


@router.message(BotState.callback_time_state)
async def on_reminder_time(message: types.Message, state: FSMContext):
    if message.text.lower() in _MENU_COMMANDS:
        await state.clear()
        return await menu_reminders(message)

    data = await state.get_data()
    time_str = message.text
    name = f"{time_str} {data['date']}"
    reminder_repo.create_recurrence_template(name, data["date"].lower(), time_str)
    reminder_repo.create_reminder(name, data["text"], message.from_user.id)
    await message.answer("✅ Напоминание создано")
    await state.clear()


# ─── Управление напоминаниями ────────────────────────────────────────────────

@router.message(F.text.lower() == "управлять напоминаниями")
async def manage_reminders(message: types.Message):
    rows = reminder_repo.get_reminders(message.from_user.id)
    if not rows:
        await message.answer("У вас нет напоминаний.")
        return

    for row in rows:
        text, is_habit, is_goal, interval, time, reminder_id, freq, start_date, active, habit_id = row
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
            await message.answer(
                f'🔔 Напоминание «{text.capitalize()}»\n'
                f'Дата: {interval}\n'
                f'Время: {str(time)[:5]}',
                reply_markup=reminder_actions_kb(reminder_id),
            )


# ─── Callback handlers ───────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data.startswith("delete_"))
async def on_delete(cb: types.CallbackQuery):
    reminder_id = int(cb.data.split("_")[1])
    reminder_repo.delete_reminder(reminder_id)
    await cb.message.delete()


@router.callback_query(lambda c: c.data.startswith("habit_"))
async def on_create_habit(cb: types.CallbackQuery, state: FSMContext):
    reminder_id = int(cb.data.split("_")[1])
    await cb.message.answer("Введите интервал повторения в днях (например: 7)")
    await state.set_state(BotState.wait_habit_frequency)
    await state.update_data(number_reminder=reminder_id)


@router.message(BotState.wait_habit_frequency)
async def on_habit_frequency(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reminder_repo.create_habit(data["number_reminder"], int(message.text))
    await message.answer("✅ Привычка создана")
    await state.clear()


@router.callback_query(lambda c: c.data.startswith("activate_"))
async def on_toggle_habit(cb: types.CallbackQuery):
    habit_id = int(cb.data.split("_")[1])
    row = reminder_repo.toggle_habit(habit_id)
    # row: habit_id, reminder_id, frequency, start_date, active, text, time
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
