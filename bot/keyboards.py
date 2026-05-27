# bot/keyboards.py — фабрика клавиатур
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Расходы"), KeyboardButton(text="Напоминания")]],
        resize_keyboard=True,
    )


def registration_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Регистрация", request_contact=True)]],
        resize_keyboard=True,
    )


def expenses_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать запись"), KeyboardButton(text="📷 Фото чека")],
            [KeyboardButton(text="Отчет по тратам"), KeyboardButton(text="📄 PDF-отчёт")],
            [KeyboardButton(text="На главное меню")],
        ],
        resize_keyboard=True,
    )


def reminders_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать напоминание")],
            [KeyboardButton(text="Управлять напоминаниями")],
            [KeyboardButton(text="На главное меню")],
        ],
        resize_keyboard=True,
    )


def location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Поделиться геолокацией", request_location=True)],
            [KeyboardButton(text="Пропустить")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def reminder_actions_kb(reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Привычка", callback_data=f"habit_{reminder_id}"),
            InlineKeyboardButton(text="Цель", callback_data=f"aim_{reminder_id}"),
        ],
        [InlineKeyboardButton(text="Удалить", callback_data=f"delete_{reminder_id}")],
    ])


def habit_toggle_kb(habit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Включить/Выключить", callback_data=f"activate_{habit_id}")]
    ])
