# bot/routers/expenses.py — запись и просмотр расходов
import io
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
from services import ocr_service
from services import pdf_service
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


@router.message(F.text == "📷 Фото чека")
async def photo_hint(message: types.Message):
    await message.answer(
        "📷 Просто отправьте фото чека прямо в чат — бот автоматически распознает позиции и запишет расходы.\n\n"
        "💡 Советы для лучшего результата:\n"
        "• Снимайте при хорошем освещении\n"
        "• Держите чек ровно, без складок\n"
        "• Текст должен быть чётким и не смазанным"
    )


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


@router.message(F.photo)
async def process_receipt_photo(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка фото чека — OCR → построчный парсинг → ML-категоризация → сохранение."""
    await message.answer("📷 Обрабатываю чек, подождите...")

    # Берём фото максимального размера (последний элемент — самое большое)
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)

    buf = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=buf)
    image_bytes = buf.getvalue()

    # OCR в отдельном потоке (blocking)
    loop = asyncio.get_running_loop()
    try:
        ocr_text = await loop.run_in_executor(None, ocr_service.recognize_receipt, image_bytes)
    except RuntimeError as e:
        await message.answer(f"❌ {e}")
        return

    if not ocr_text:
        await message.answer("❌ Не удалось распознать текст. Попробуйте сфотографировать чётче при хорошем освещении.")
        return

    logger.info(f"OCR text: {ocr_text[:200]}")

    # Сначала пробуем построчный парсер чека
    receipt_items = await loop.run_in_executor(None, ocr_service.parse_receipt_text, ocr_text)

    if receipt_items:
        # Нашли позиции в формате чека
        categories = await asyncio.gather(*[
            _predict_async(name) for name, _ in receipt_items
        ])
        items = [(cat, name, amount) for (name, amount), cat in zip(receipt_items, categories)]
        mode = "receipt"
    else:
        # Fallback: парсим как обычный текст (натурально написанный)
        segments = await _split_async(ocr_text)
        items = [
            (category, desc, amount)
            for (desc, amount, _), category in zip(
                segments,
                await asyncio.gather(*[_predict_async(_category_snippet(d, ocr_text)) for d, _, _ in segments]),
            )
        ]
        mode = "text"

    if not items:
        await message.answer(
            f"🔍 Распознан текст:\n<pre>{ocr_text[:400]}</pre>\n\n"
            f"❌ Не удалось выделить позиции с суммами.",
            parse_mode="HTML",
        )
        return

    # Сохраняем OCR-текст в voice_message (поле audio_data = file_id фото)
    await database.expenses.save_voice_message(ocr_text, file_info.file_path)

    # Сохраняем расходы
    await database.expenses.save_expense_items(message.from_user.id, items, file_info.file_path)

    lines = "\n".join(
        f"• {f'{amt:.2f}' if amt else '?'} BYN → «{cat}» ({desc})"
        for cat, desc, amt in items
    )
    hint = "" if mode == "receipt" else "\n\n💡 Формат чека не распознан — применён универсальный парсер."
    await message.answer(
        f"📷 Чек обработан, записано {len(items)} позиций:\n{lines}{hint}"
    )


@router.message(F.text == "📄 PDF-отчёт")
async def send_pdf_report(message: types.Message, bot: Bot):
    """Генерирует PDF-отчёт за текущий месяц и отправляет файлом."""
    now = datetime.now()
    await message.answer("⏳ Генерирую отчёт...")

    rows = await database.expenses.get_expenses(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name or "user"

    loop = asyncio.get_running_loop()
    pdf_bytes = await loop.run_in_executor(
        None, pdf_service.generate_monthly_report, rows, username, now.year, now.month
    )

    month_names = [
        "", "январь", "февраль", "март", "апрель", "май", "июнь",
        "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
    ]
    filename = f"report_{month_names[now.month]}_{now.year}.pdf"

    from aiogram.types import BufferedInputFile
    await message.answer_document(
        BufferedInputFile(pdf_bytes, filename=filename),
        caption=f"📄 Отчёт за {month_names[now.month]} {now.year}",
    )


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
