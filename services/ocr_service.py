# services/ocr_service.py — OCR-распознавание текста с фото чека
import io
import os
import re
import logging

logger = logging.getLogger(__name__)

# Возможные пути к Tesseract на Windows
_TESSERACT_WIN_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\USER\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\tools\Tesseract-OCR\tesseract.exe",
]

# Фильтр строк-«мусора» с чека (служебные строки, которые не являются товарами)
_RECEIPT_SKIP_RE = re.compile(
    r"^(?:"
    r"итого|сумма|итог|к\s*оплате|оплачено|наличн|безналичн|сдача|получено"
    r"|скидк|бонус|баллы|начислено|списано"
    r"|ндс|налог|акциз"
    r"|кассир|оператор|кассовый\s*чек|фискальн"
    r"|спасибо|приятного|до\s*свидания"
    r"|чек|дата|время|смена|номер|магазин|адрес|телефон|сайт"
    r"|инн|кпп|огрн|октмо|фн|фд|фп|рнм|зн"
    r"|товарный\s*чек|кол[-\s]?во|количество|цена|стоимость|наименование"
    r"|код\s*товара|штрих|артикул"
    r"|www\.|http"
    r")",
    re.IGNORECASE,
)

# Цена на конце строки: 1.99 / 1,99 / 199
_PRICE_END_RE = re.compile(r"(\d{1,6}[.,]\d{2})\s*[*х×x]?\s*$")
# Строка с «кол-во × цена = итог»: "1 × 2.99 = 2.99"
_QTY_PRICE_RE = re.compile(r"\d+\s*[*×хx]\s*(\d+[.,]\d{2})\s*=\s*(\d+[.,]\d{2})\s*$", re.IGNORECASE)


def _setup_tesseract() -> bool:
    """Проверяет и настраивает путь к Tesseract. Возвращает True если доступен."""
    try:
        import pytesseract
        # На Windows перебираем известные пути
        if os.name == "nt":
            for path in _TESSERACT_WIN_PATHS:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Tesseract найден: {path}")
                    break
        # Проверяем что tesseract вообще запускается (может быть в PATH)
        pytesseract.get_tesseract_version()
        return True
    except Exception as e:
        logger.warning(f"Tesseract недоступен: {e}")
        return False


def _preprocess(image_bytes: bytes):
    """
    Препроцессинг изображения для улучшения качества OCR:
    - перевод в оттенки серого
    - усиление контраста
    - небольшое увеличение (если изображение мелкое)
    """
    from PIL import Image, ImageEnhance, ImageFilter

    img = Image.open(io.BytesIO(image_bytes))

    # Масштабируем маленькие изображения — Tesseract лучше работает с крупными
    w, h = img.size
    if max(w, h) < 1000:
        scale = 1000 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    img = img.convert("L")                          # grayscale
    img = ImageEnhance.Contrast(img).enhance(2.0)  # контраст ×2
    img = img.filter(ImageFilter.SHARPEN)           # резкость

    return img


def recognize_receipt(image_bytes: bytes) -> str:
    """
    Запускает OCR на фото чека.
    Возвращает распознанный текст или пустую строку при ошибке.
    """
    if not _setup_tesseract():
        raise RuntimeError(
            "Tesseract не установлен. Скачайте с https://github.com/UB-Mannheim/tesseract/wiki "
            "и установите с русским языковым пакетом (rus.traineddata)."
        )

    import pytesseract

    try:
        img = _preprocess(image_bytes)
        # PSM 6 — «единый блок текста» (таблица без явной разметки)
        text = pytesseract.image_to_string(img, lang="rus+eng", config="--psm 6 --oem 3")
        return text.strip()
    except Exception as e:
        logger.error(f"OCR ошибка: {e}", exc_info=True)
        return ""


def parse_receipt_text(text: str) -> list[tuple[str, float]]:
    """
    Парсит текст чека построчно и извлекает пары (название товара, сумма).

    Поддерживает форматы:
        МОЛОКО 1Л            89.90
        ХЛЕБ                 45.00
        1 × 45.00 = 45.00         (строка кол-во × цена)

    Возвращает список (название, сумма_float).
    """
    results: list[tuple[str, float]] = []
    lines = text.splitlines()

    # Пытаемся определить — это чек или нет.
    # Если меньше 2 строк с ценами в конце — вероятно, это обычное фото, не чек.

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue

        # Пропускаем служебные строки
        if _RECEIPT_SKIP_RE.match(line):
            continue

        # Формат «кол-во × цена = итог» — берём итог
        m_qty = _QTY_PRICE_RE.search(line)
        if m_qty:
            # Это подстрока описания количества, не товар — пропускаем
            continue

        # Стандартный формат: «НАЗВАНИЕ ... ЦЕНА»
        m = _PRICE_END_RE.search(line)
        if m:
            amount_str = m.group(1).replace(",", ".")
            try:
                amount = float(amount_str)
            except ValueError:
                continue

            if amount <= 0 or amount > 1_000_000:
                continue

            # Название — всё до суммы, очищаем цифры-«мусор»
            name = line[: m.start()].strip()
            # Убираем коды товаров в начале (5-13 цифр) и артикулы
            name = re.sub(r"^\d{5,13}\s*", "", name)
            name = re.sub(r"\s{2,}", " ", name).strip(" .,*-")

            if len(name) < 2:
                continue

            results.append((name, amount))

    return results
