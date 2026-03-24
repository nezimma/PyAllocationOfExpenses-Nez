# bot/routers/expenses.py — запись и просмотр расходов
import os
import asyncio
import tempfile
import logging
from datetime import datetime

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from bot.states import BotState
from bot.keyboards import expenses_menu, main_menu
from database import expenses as expense_repo
from cloud import disk
from services.speech_service import SpeechRecognitionService
from ml import model_svc

logger = logging.getLogger(__name__)
router = Router()
_speech = SpeechRecognitionService()


@router.message(F.text.lower() == "расходы")
async def menu_expenses(message: types.Message):
    await message.answer("Меню расходов", reply_markup=expenses_menu())


@router.message(F.text.lower() == "создать запись")
async def start_recording(message: types.Message, state: FSMContext):
    await message.answer("Отправьте голосовое сообщение для записи расхода")
    await state.set_state(BotState.sell_state)


@router.message(BotState.sell_state, F.voice)
async def process_voice(message: types.Message, state: FSMContext, bot: Bot):
    # Сохраняем аудио во временный файл
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        ogg_path = tmp.name
    wav_path = ogg_path.replace(".ogg", ".wav")

    file_info = await bot.get_file(message.voice.file_id)
    await bot.download_file(file_info.file_path, destination=ogg_path)

    # Бекап в облако (фоновая задача)
    asyncio.create_task(_backup_async(ogg_path, message.from_user.id))

    # Распознавание речи
    recognized = await _recognize_async(ogg_path, wav_path)
    logger.info(f"Recognized: {recognized}")

    expense_repo.save_voice_message(recognized, file_info.file_path)

    if recognized in ("Не удалось распознать речь", "Ошибка сервиса распознавания речи"):
        await message.answer(f"❌ {recognized}")
    else:
        category = await _predict_async(recognized)
        expense_repo.save_expense(message.from_user.id, category, file_info.file_path)
        await message.answer(f"🎤 Покупка записана в «{category}»")

    # Чистим временные файлы
    for path in (ogg_path, wav_path):
        if os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


@router.message(F.text.lower() == "отчет по тратам")
async def report(message: types.Message):
    rows = expense_repo.get_expenses(message.from_user.id)
    if not rows:
        await message.answer("Расходов пока нет.")
        return

    for amount, desc, created_at, category in rows:
        dt = str(created_at)
        date_str, time_str = dt.split()[0], dt.split()[1][:5]
        await message.answer(
            f"💳 Категория: {category}\n"
            f"📄 Трата: {desc}\n"
            f"💰 Сумма: {amount} BYN\n"
            f"🕒 {date_str} {time_str}"
        )

    now = datetime.now()
    total = 0
    by_category: dict[str, float] = {}
    for amount, _, created_at, category in rows:
        if created_at.month == now.month and created_at.year == now.year:
            total += amount
            by_category[category] = by_category.get(category, 0) + amount

    summary = "\n".join(f"{cat}: {amt:.2f} BYN" for cat, amt in by_category.items())
    await message.answer(f"{summary}\nВсего потрачено: {total:.2f} BYN")


# ─── Async wrappers ──────────────────────────────────────────────────────────

async def _backup_async(path: str, user_id: int):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, disk.backup, path, user_id)


async def _recognize_async(ogg_path: str, wav_path: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _speech.convert_and_recognize, ogg_path, wav_path)


async def _predict_async(text: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, model_svc.predict_category, text)
