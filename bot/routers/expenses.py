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
import database
from database.text_parser import split_multi_expenses
from cloud import disk
from services.speech_service import SpeechRecognitionService
import ml

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
async def process_voice_from_state(message: types.Message, state: FSMContext, bot: Bot):
    """Голосовое из явного FSM-состояния (через кнопку «Создать запись»)."""
    await _handle_voice(message, bot, state)
    # state.clear() вызывается внутри, если не переходим в waiting_for_amount


@router.message(F.voice)
async def process_voice_any(message: types.Message, state: FSMContext, bot: Bot):
    """Голосовое в любой момент — автоматически пишется как трата."""
    await _handle_voice(message, bot, state)


# ─── Общая логика обработки голосового ──────────────────────────────────────

async def _handle_voice(message: types.Message, bot: Bot, state: FSMContext):
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        ogg_path = tmp.name
    wav_path = ogg_path.replace(".ogg", ".wav")

    file_info = await bot.get_file(message.voice.file_id)
    await bot.download_file(file_info.file_path, destination=ogg_path)

    backup_task = asyncio.create_task(_backup_async(ogg_path, message.from_user.id))
    recognized = await _recognize_async(ogg_path, wav_path)

    try:
        await backup_task
    except Exception as e:
        logger.error(f"Backup failed: {e}")

    logger.info(f"Recognized: {recognized}")
    await database.expenses.save_voice_message(recognized, file_info.file_path)

    if recognized in ("Не удалось распознать речь", "Ошибка сервиса распознавания речи"):
        await message.answer(f"❌ {recognized}")
    else:
        segments = await _split_async(recognized)
        categories = await asyncio.gather(*[
            _predict_async(_category_snippet(desc, recognized))
            for desc, _, _ in segments
        ])

        items = [
            (category, desc, amount)
            for (desc, amount, _), category in zip(segments, categories)
        ]

        if len(items) == 1:
            category, desc, amount = items[0]
            if amount is None:
                # Не сохраняем — ждём сумму от пользователя
                await message.answer(
                    f"🎤 Распознано: «{desc or recognized}» → категория «{category}»\n"
                    f"💬 Сумму не удалось определить. Введите сумму вручную (например: 150.50):"
                )
                await state.set_state(BotState.waiting_for_amount)
                await state.update_data(pending_audio=file_info.file_path, pending_items=items)
                return
            await database.expenses.save_expense_items(message.from_user.id, items, file_info.file_path)
            await message.answer(f"🎤 Покупка записана в «{category}»")
        else:
            await database.expenses.save_expense_items(message.from_user.id, items, file_info.file_path)
            missing_count = sum(1 for _, _, amt in items if amt is None)
            lines = "\n".join(
                f"• {amt or '?'} → «{cat}» ({desc})"
                for cat, desc, amt in items
            )
            await message.answer(f"🎤 Записано {len(items)} покупок:\n{lines}")
            if missing_count:
                await message.answer(
                    f"⚠️ Для {missing_count} покупок не найдена сумма. "
                    f"Исправьте их в разделе «Расходы»."
                )

    for path in (ogg_path, wav_path):
        if os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


@router.message(BotState.waiting_for_amount, F.text)
async def receive_manual_amount(message: types.Message, state: FSMContext):
    """Пользователь вводит сумму вручную после нераспознанного голосового."""
    text = message.text.strip().replace(",", ".")
    try:
        amount = float(text)
    except ValueError:
        await message.answer("❌ Не удалось разобрать сумму. Введите число, например: 150 или 89.99")
        return

    data = await state.get_data()
    items: list[tuple[str, str, float | None]] = data.get("pending_items", [])
    audio_path: str = data.get("pending_audio", "")

    # Подставляем сумму в первую позицию без суммы
    updated = []
    filled = False
    for cat, desc, amt in items:
        if amt is None and not filled:
            updated.append((cat, desc, amount))
            filled = True
        else:
            updated.append((cat, desc, amt))

    await database.expenses.save_expense_items(message.from_user.id, updated, audio_path)
    await state.clear()
    await message.answer(f"✅ Сумма {amount:.2f} сохранена!")


@router.message(F.text.lower() == "отчет по тратам")
async def report(message: types.Message):
    rows = await database.expenses.get_expenses(message.from_user.id)
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
            amt = float(amount) if amount is not None else 0.0
            total += amt
            by_category[category] = by_category.get(category, 0) + amt

    summary = "\n".join(f"{cat}: {amt:.2f} BYN" for cat, amt in by_category.items())
    await message.answer(f"{summary}\nВсего потрачено: {total:.2f} BYN")


def _category_snippet(desc: str, fallback: str) -> str:
    """Берёт последние 12 слов описания — ближайший контекст к сумме, без мусора в начале."""
    text = (desc or fallback).strip()
    words = text.split()
    return " ".join(words[-12:]) if len(words) > 12 else text


# ─── Async wrappers ──────────────────────────────────────────────────────────

async def _backup_async(path: str, user_id: int):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, disk.backup, path, user_id)


async def _recognize_async(ogg_path: str, wav_path: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _speech.convert_and_recognize, ogg_path, wav_path)


async def _split_async(text: str) -> list[tuple]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, split_multi_expenses, text)


async def _predict_async(text: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ml.model_svc.predict_category, text)
