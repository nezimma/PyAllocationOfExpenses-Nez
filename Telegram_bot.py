import aiogram
import asyncio
from aiogram import Dispatcher, Bot, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import Data_base

API = '8231618759:AAFQiJ2pUf6ds8Gx4Ze41vVaiUjJoOAMTlU'
host = "localhost"
user = "postgres"
password = "12345"
db_name = "postgres"
bot = Bot(token=API)
dp = Dispatcher()
db = Data_base.Postgresql(host, user, password, db_name)

class BotState(StatesGroup):
    sell_state = State()
    willsell_state = State()
    callback_state = State()
    aim_state = State()

@dp.message(Command("start"))
async def login_user(message: types.Message):
    kb = [[types.KeyboardButton(text="Регистрация", request_contact=True)]]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True
    )
    await message.answer("добропожаловаться", reply_markup=keyboard)

@dp.message(F.contact)
async def input_panel(message:types.Message):
    if message.contact is not None:
        await message.answer("Регистрация прошла успешно")
        phone = str(message.contact.phone_number)
        user_id = int(message.from_user.id)
        db.loggin(login=user_id, phone_num=phone)






@dp.callback_query()
async def main_start():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main_start())
