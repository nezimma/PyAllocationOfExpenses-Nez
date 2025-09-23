import os
import tempfile

from pydub import AudioSegment
import aiogram
import subprocess
import asyncio
from aiogram import Dispatcher, Bot, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import Data_base
import Learning_model
import Speech_Recognition

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
        kb = [[types.KeyboardButton(text="Расходы"),
                types.KeyboardButton(text="Напоминания")]]
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True
        )
        await message.answer("Регистрация прошла успешно", reply_markup=keyboard)
        phone = str(message.contact.phone_number)
        user_id = int(message.from_user.id)
        db.loggin(login=user_id, phone_num=phone)

@dp.message(F.text.lower() == "расходы")
async def get_voice(message: types.Message, state:FSMContext):
    await message.answer("Отправляйте голосовые сообщения для записей своих расходов")
    await state.set_state(BotState.sell_state)

@dp.message(BotState.sell_state, F.voice)
async def state_processing_voice(message: types.Message, state:FSMContext):
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_ogg:
        ogg_path = tmp_ogg.name
    wav_path = ogg_path.replace('.ogg', '.wav')
    try:
        voice = message.voice
        file_info = await bot.get_file(voice.file_id)
        file_path = file_info.file_path

        await bot.download_file(file_path, destination=ogg_path)

        ffmpeg_cmd = [
            'ffmpeg', '-i', ogg_path,
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            wav_path
        ]

        result = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )

        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr.decode()}")
            await message.answer("❌ Ошибка обработки аудио")
            return

        if not os.path.exists(wav_path):
            await message.answer("❌ Файл не был создан")
            return

        speech_processor = Speech_Recognition.Speech_voice()
        recognized_text = speech_processor.convertation(wav_path)
        print(f"Результат распознавания: {recognized_text}")

        if recognized_text in ["Не удалось распознать речь", "Ошибка сервиса распознавания речи"]:
            await message.answer(f"❌ {recognized_text}")
            return

        await message.answer(f"🎤 {Learning_model.accuracy_text(recognized_text)}")

        await state.update_data(recognized_text=recognized_text)

    except subprocess.TimeoutExpired:
        await message.answer("❌ Таймаут обработки аудио")
    except Exception as e:
        print(f"Error in voice processing: {e}")
        await message.answer("❌ Произошла ошибка при обработке голосового сообщения")
    finally:
        # Удаляем временные файлы
        for file_path in [ogg_path, wav_path]:
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except:
                    pass









@dp.callback_query()
async def main_start():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main_start())
