# bot/states.py — FSM-состояния телеграм-бота
from aiogram.fsm.state import StatesGroup, State


class BotState(StatesGroup):
    sell_state = State()              # ожидание голосового сообщения для расхода
    callback_text_state = State()     # ввод названия напоминания
    callback_date_state = State()     # ввод даты напоминания
    callback_time_state = State()     # ввод времени напоминания
    waiting_for_password = State()    # ввод пароля при регистрации
    waiting_for_location = State()    # ожидание геолокации после регистрации
    wait_habit_frequency = State()    # ввод частоты привычки
    waiting_for_amount = State()      # ввод суммы вручную (если не распознана)
