import os
import tempfile
import asyncio
from aiogram import Dispatcher, Bot, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

import Cloudwork
from Data_base import db
from datetime import date, datetime
import re
import Learning_model
import Speech_Recognition

API = '8231618759:AAFQiJ2pUf6ds8Gx4Ze41vVaiUjJoOAMTlU'
bot = Bot(token=API)
dp = Dispatcher()
host = "localhost"
user = "postgres"
password_service = "12345"
db_name = "allocationofexpenses"

db.init_model_table()
Learning_model.init_model()


class BotState(StatesGroup):
    sell_state = State()
    callback_text_state = State()
    callback_time_state = State()
    callback_date_state = State()
    waiting_for_password = State()
    wait_habit_frequency = State()



@dp.message(Command('click'))
async def click_mat(message: types.Message):
    await bot.send_message(chat_id=748256674, text='Покупка записана в Рестораны и еда')
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

@dp.message(F.text.lower() == 'расходы')
async def menu_expenses(message: types.Message):
    kb = [[types.KeyboardButton(text="Создать запись")],
          [types.KeyboardButton(text="Отчет по тратам")],
          [types.KeyboardButton(text="На главное меню")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Добро пожаловать в меню расходов", reply_markup=keyboard)

@dp.message(F.text.lower() == "отчет по тратам")
async def report_expenses(message: types.Message):
    rows = db.return_expenses(message.from_user.id)

    for amount, desc, created_at, category in rows:
        await message.answer(
            f"💳 Категория: {category}\n"
            f"📄 Трата: {desc}\n"
            f"💰 Сумма: {amount} BYN\n"
            f"🕒 Дата и время: {str(created_at).split()[0]} {str(created_at).split()[1][:5]}"
        )
    total = 0
    category_month = {}

    now = datetime.now()
    current_month = now.month
    current_year = now.year

    for amount, desc, created_at, category in rows:
        if created_at.month == current_month and created_at.year == current_year:
            total += amount
            category_month[category] = category_month.get(category, 0) + amount

    text = ''
    for category, amount in category_month.items():
        text += f'{category}: {amount:.2f} BYN\n'
    text += f'Всего потрачено {total}'
    await message.answer(text)



@dp.message(F.text.lower() == "создать запись")
async def get_voice(message: types.Message, state:FSMContext):
    await message.answer("Отправляйте голосовые сообщения для записей своих расходов")
    await state.set_state(BotState.sell_state)

@dp.message(BotState.sell_state, F.voice)
async def state_processing_voice(message: types.Message, state:FSMContext):
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_ogg:
        ogg_path = tmp_ogg.name
    wav_path = ogg_path.replace('.ogg', '.wav')

    voice = message.voice
    file_info = await bot.get_file(voice.file_id)
    file_path = file_info.file_path
    await bot.download_file(file_path, destination=ogg_path)


    asyncio.create_task(run_backup_async(ogg_path, message.from_user.id))
    print(file_path)
    recognized_text = await recognize_async(ogg_path, wav_path)
    print(f"Результат распознавания: {recognized_text}")

    db.voice_recognize(recognized_text, file_path)



    if recognized_text in ["Не удалось распознать речь", "Ошибка сервиса распознавания речи"]:
        await message.answer(f"❌ {recognized_text}")
        return None

    recognized_category = await predict_async(recognized_text)
    await message.answer(f"🎤 Покупка записана в {recognized_category}")
    db.expenses(message.from_user.id, recognized_category, file_path)
    await state.update_data(recognized_text=recognized_text)


    # Удаляем временные файлы
    for file_path in [ogg_path, wav_path]:
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except:
                pass

#ассинхронная обертка для облака
async def run_backup_async(path, user_id):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        Cloudwork.backup,
        path,
        user_id
    )

#ассинхронная обертка для перевода в текст
async def recognize_async(ogg_path, wav_path):
    loop = asyncio.get_running_loop()
    speech_processor = Speech_Recognition.Speech_voice()

    return await loop.run_in_executor(
        None,
        speech_processor.convertation,
        ogg_path,
        wav_path
    )

#ассинхронная обортка для предсказания текста
async def predict_async(text):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        Learning_model.predict_category,
        text
    )


@dp.message(F.text.lower() == "напоминания")
async def start_callback(message: types.Message):
    kb = [[types.KeyboardButton(text="Создать напоминание")],
          [types.KeyboardButton(text="Управлять напоминаниями")],
          [types.KeyboardButton(text="На главное меню")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Создавайте Напоминания, создавайте привычки и задавайте Цели", reply_markup=keyboard)

@dp.message(F.text.lower() == "на главное меню")
async def back_main_menu(message: types.Message):
    kb = [[types.KeyboardButton(text="Расходы"),
           types.KeyboardButton(text="Напоминания")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Вы вернулись на главное меню", reply_markup=keyboard)

@dp.message(F.text.lower() == "создать напоминание")
async def craft_callback(message: types.Message, state:FSMContext):
    await message.answer("Введите название напоминания")
    await state.set_state(BotState.callback_text_state)

@dp.message(BotState.callback_text_state)
async def text_callback(message: types.Message, state: FSMContext):
    text = message.text
    if text in ['Управлять напоминаниями', 'На главное меню', 'Создать напоминание']:
        await manege_callback(message)
    else:
        await state.update_data(text=str(text))
        await message.answer("введите дату в формате 2025.01.01")
        await state.set_state(BotState.callback_date_state)

@dp.message(BotState.callback_date_state)
async def date_callback(message:types.Message, state: FSMContext):
    date = message.text
    if date in ['Управлять напоминаниями', 'На главное меню', 'Создать напоминание']:
        await manege_callback(message)
    else:
        await state.update_data(date=str(date))
        await message.answer("Введите время в формате 12:00")
        await state.set_state(BotState.callback_time_state)

@dp.message(BotState.callback_time_state)
async def time_callback(message: types.Message, state: FSMContext):
    time = message.text
    if time in ['Управлять напоминаниями', 'На главное меню', 'Создать напоминание']:
        await manege_callback(message)
    else:
        text_date = await state.get_data()
        db.reccurent_templates(time+' '+text_date['date'], text_date['date'].lower(), time)
        user_id = message.from_user.id
        db.reminder(time+' '+text_date['date'], str(text_date["text"]), user_id)
        await message.answer("Запись выполнена успешно")
        await state.clear()

@dp.message(F.text.lower() == 'управлять напоминаниями')
async def manege_callback(message: types.Message):
    mass = []
    user_id = message.from_user.id
    rows = db.call_reminder(user_id)
    print(rows)
    for row in rows:
        for i in range(len(row)):
            mass.append(row[i])
        if mass[6] != None:
            delta = date.today() - mass[7]
            activiti = 'Активно' if mass[8] else 'Не активно'
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='Включить/Выключить', callback_data=f"activate_{mass[9]}")]])
            await message.answer(f'Привычка "{mass[0].capitalize()}"\n'
                                 f'Интевал повторения "{mass[6]}"\n'
                                 f'Следующее напоминание через "{str(delta.days % int(mass[6])) + "дней" if delta.days % int(mass[6]) != 0 else "Сегодня"} в {str(mass[4])[:5]}"\n'
                                 f'Активность "{activiti}"', reply_markup=inline_kb)
        else:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text='Привычка', callback_data=f"habit_{mass[5]}"),
                        InlineKeyboardButton(text='Цель', callback_data=f'aim_{mass[5]}')],
                        [InlineKeyboardButton(text='Удалить', callback_data=f'delete_{mass[5]}')]])
            await message.answer(f'Напоминание "{mass[0].capitalize()}"\n'
                                 f'Дата напоминания "{mass[3]}"\n'
                                 f'Время вызова "{str(mass[4])[:5]}"', reply_markup=inline_kb)
        mass.clear()

@dp.callback_query(lambda c: c.data.startswith('delete'))
async def delete_reminder(cb: types.CallbackQuery):
    await cb.message.delete()
    db.delete_reminder(cb.data.split('_')[1])

@dp.callback_query(lambda c: c.data.startswith('habit'))
async def create_habit(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("Для создания привычки введите интервал через который будет отправлено вам напоминание")
    await state.set_state(BotState.wait_habit_frequency)
    await state.update_data(number_reminder= cb.data.split('_')[1])

@dp.message(BotState.wait_habit_frequency)
async def get_frequency(message: types.Message, state: FSMContext):
    frequency = message.text
    remind_id = await state.get_data()
    remind_id = remind_id.get('number_reminder')
    db.create_habit(frequency, remind_id)
    await message.answer("Привычка создана")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("activate"))
async def on_off(cb: types.CallbackQuery):
    habit_id = cb.data.split("_")[1]
    row = db.review_habit_active(habit_id)
    print(row)
    # await cb.answer()
    delta = date.today() - row[3]
    activiti = 'Активно' if row[4] else 'Не активно'
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='Включить/Выключить', callback_data=f"activate_{row[0]}")]])
    await cb.message.edit_text(f'Привычка "{row[5].capitalize()}"\n'
                         f'Интевал повторения "{row[2]}"\n'
                         f'Следующее напоминание через "{str(delta.days % int(row[2])) + "дней" if delta.days % int(row[2]) != 0 else "Сегодня"} в {str(row[6])[:5]}"\n'
                         f'Активность "{activiti}"', reply_markup=inline_kb)






@dp.callback_query()
async def main_start():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main_start())
