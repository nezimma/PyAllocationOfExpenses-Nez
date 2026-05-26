import logging
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from timezonefinder import TimezoneFinder

from bot.states import BotState
from bot.keyboards import registration_kb, main_menu, location_kb
import database

logger = logging.getLogger(__name__)
router = Router()

_tf = TimezoneFinder()

_LOCATION_PROMPT = (
    "📍 Чтобы напоминания приходили точно вовремя, боту нужно знать ваш часовой пояс.\n\n"
    "Нажмите «Поделиться геолокацией» — бот определит пояс автоматически и больше не будет спрашивать.\n\n"
    "Можно пропустить и задать местоположение позже в настройках."
)


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
    if not message.text:
        await message.answer("Пожалуйста, введите пароль текстом.")
        return
    data = await state.get_data()
    await database.users.register(
        telegram_id=data["user_id"],
        login=data["phone"],
        password=message.text,
    )
    await state.set_state(BotState.waiting_for_location)
    await message.answer(_LOCATION_PROMPT, reply_markup=location_kb())


@router.message(BotState.waiting_for_location, F.location)
async def on_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lng = message.location.longitude
    tz_str = _tf.timezone_at(lat=lat, lng=lng)

    if tz_str:
        await database.users.set_timezone(message.from_user.id, tz_str)
        await message.answer(
            f"✅ Часовой пояс определён: {tz_str}\n"
            "Напоминания будут приходить точно по вашему времени.",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            "Не удалось определить часовой пояс по геолокации. Используем Europe/Minsk по умолчанию.",
            reply_markup=main_menu(),
        )

    await state.clear()


@router.message(BotState.waiting_for_location, F.text == "Пропустить")
async def on_location_skip(message: types.Message, state: FSMContext):
    await message.answer(
        "Хорошо! Используем Europe/Minsk по умолчанию.\n"
        "Изменить можно позже в настройках.",
        reply_markup=main_menu(),
    )
    await state.clear()
