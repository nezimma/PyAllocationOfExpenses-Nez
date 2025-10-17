import os
import tempfile
import asyncio
from aiogram import Dispatcher, Bot, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from Data_base import db
import re
# import Learning_model
import Speech_Recognition

API = '8231618759:AAFQiJ2pUf6ds8Gx4Ze41vVaiUjJoOAMTlU'
bot = Bot(token=API)
dp = Dispatcher()
host = "localhost"
user = "postgres"
password_service = "12345"
db_name = "allocationofexpenses"

interval = {"неделя":7,
            "день":1}



class BotState(StatesGroup):
    sell_state = State()
    callback_text_state = State()
    callback_time_state = State()
    callback_date_state = State()
    waiting_for_password = State()




@dp.message(Command('click'))
async def click_mat(message: types.Message):
    await bot.send_message(chat_id=1513094869, text='хихихиххихихихихих')
@dp.message(Command("start"))
async def login_user(message: types.Message):
    kb = [[types.KeyboardButton(text="Регистрация", request_contact=True)]]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True
    )
    await message.answer("добропожаловаться", reply_markup=keyboard)



@dp.message(F.contact)
async def input_panel(message:types.Message, state: FSMContext):
    if message.contact is not None:
        await message.answer('Придумайте пароль:')
        await state.set_state(BotState.waiting_for_password)
        await state.update_data(
            phone=str(message.contact.phone_number),
            user_id=int(message.from_user.id)

        )

@dp.message(BotState.waiting_for_password)
async def process_message(message: types.Message, state:FSMContext):
    password = message.text
    data = await state.get_data()  # достаем сохранённые ранее данные
    phone = data.get('phone')
    user_id = data.get('user_id')

    await message.answer(f'Был записан пароль: {password}')

    # Создаём объект подключения к базе
    print(user_id, phone, password)
    db.loggin(unical_code=user_id, login=phone, password=password)

    # Используем клавиатуру и отправляем сообщение
    kb = [[types.KeyboardButton(text="Расходы"),
           types.KeyboardButton(text="Напоминания")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Регистрация прошла успешно", reply_markup=keyboard)
    await state.clear()

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

        with open(ogg_path, 'rb') as f:
            audio_bytes = f.read()

        speech_processor = Speech_Recognition.Speech_voice()
        recognized_text = speech_processor.convertation(ogg_path, wav_path)
        print(f"Результат распознавания: {recognized_text}")

        db.voice_recognize(recognized_text, audio_bytes)

        if recognized_text in ["Не удалось распознать речь", "Ошибка сервиса распознавания речи"]:
            await message.answer(f"❌ {recognized_text}")
            return


        # await message.answer(f"🎤 {Learning_model.accuracy_text(recognized_text)}")

        await state.update_data(recognized_text=recognized_text)

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

@dp.message(F.text.lower() == "напоминания")
async def start_callback(message: types.Message):
    kb = [[types.KeyboardButton(text="Создать напоминание")],
          [types.KeyboardButton(text="Управлять напоминаниями")],
          [types.KeyboardButton(text="Назад")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Создавайте Напоминания, создавайте привычки и задавайте Цели", reply_markup=keyboard)


@dp.message(F.text.lower() == "создать напоминание")
async def craft_callback(message: types.Message, state:FSMContext):
    await message.answer("Введите название напоминания")
    await state.set_state(BotState.callback_text_state)

@dp.message(BotState.callback_text_state)
async def text_callback(message: types.Message, state: FSMContext):
    text = message.text
    await state.update_data(text=str(text))
    await message.answer("введите дату или интервал")
    await state.set_state(BotState.callback_date_state)

@dp.message(BotState.callback_date_state)
async def date_callback(message:types.Message, state: FSMContext):
    date = message.text
    await state.update_data(date=str(date))
    await message.answer("Введите время")
    await state.set_state(BotState.callback_time_state)

@dp.message(BotState.callback_time_state)
async def time_callback(message: types.Message, state: FSMContext):
    time = message.text
    text_date = await state.get_data()
    db.reccurent_templates(time+' '+text_date['date'], interval[text_date['date']], time)
    user_id = message.from_user.id
    db.reminder(time+' '+text_date['date'], text_date["text"], user_id)
    await message.answer("Запись выполнена успешно")
    await state.clear()

@dp.message(F.text.lower() == 'управлять напоминаниями')
async def manege_callback(message: types.Message):
    mass = []
    inverse_interval = {v: k for k, v in interval.items()}
    user_id = message.from_user.id
    rows = db.call_reminder(user_id)
    for row in rows:
        for i in range(len(row)):
            mass.append(row[i])
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text='Привычка', callback_data=f"habit_{mass[5]}"),
                    InlineKeyboardButton(text='Цель', callback_data=f'aim_{mass[5]}')]])
        await message.answer(f'Напоминание "{mass[0].capitalize()}"\n'
                             f'Интервал повторения "{inverse_interval[mass[3]].capitalize()}"\n'
                             f'Время вызова "{mass[4]}"', reply_markup=inline_kb)









# password = message.text
#     data = await state.get_data()  # достаем сохранённые ранее данные
#     phone = data.get('phone')
#     user_id = data.get('user_id')
#
#     await message.answer(f'Был записан пароль: {password}')
#
#     # Создаём объект подключения к базе
#     print(user_id, phone, password)
#     db.loggin(unical_code=user_id, login=phone, password=password)
#
#     # Используем клавиатуру и отправляем сообщение
#     kb = [[types.KeyboardButton(text="Расходы"),
#            types.KeyboardButton(text="Напоминания")]]
#     keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
#     await message.answer("Регистрация прошла успешно", reply_markup=keyboard)
#     await state.clear()






@dp.callback_query()
async def main_start():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main_start())
