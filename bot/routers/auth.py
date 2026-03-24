# bot/routers/auth.py — регистрация пользователя
import logging
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from bot.states import BotState
from bot.keyboards import registration_kb, main_menu
from database import users

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать!", reply_markup=registration_kb())


@router.message(F.contact)
async def on_contact(message: types.Message, state: FSMContext):
    await message.answer("Придумайте пароль:")
    await state.set_state(BotState.waiting_for_password)
    await state.update_data(
        phone=str(message.contact.phone_number),
        user_id=int(message.from_user.id),
    )


@router.message(BotState.waiting_for_password)
async def on_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    users.register(
        telegram_id=data["user_id"],
        login=data["phone"],
        password=password,
    )
    await message.answer("Регистрация прошла успешно", reply_markup=main_menu())
    await state.clear()
