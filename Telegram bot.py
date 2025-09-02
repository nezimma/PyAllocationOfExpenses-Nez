import aiogram
import asyncio
from aiogram import Dispatcher, Bot, types
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, InlineKeyboardButton
from aiogram.fsm.context import FSMContext


API = '8231618759:AAFQiJ2pUf6ds8Gx4Ze41vVaiUjJoOAMTlU'

bot = Bot(token=API)
dp = Dispatcher()

class BotState(StatesGroup):
    sell_state = State()
    willsell_state = State()
    callback_state = State()
    aim_state = State()

@dp.message(Command("start"))
async def login_user(message: types.Message):
    kb = [[types.KeyboardButton(text="Регистрация"), ]]


