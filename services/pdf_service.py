# services/pdf_service.py — генерация PDF-отчёта по тратам за месяц
import io
import os
from datetime import datetime
from collections import defaultdict

# ── Шрифты (Cyrillic) ─────────────────────────────────────────────────────────
# Пробуем Arial из Windows, затем DejaVu если есть, иначе Helvetica (без кириллицы)
_FONT_CANDIDATES = [
    ("Arial",      r"C:\Windows\Fonts\arial.ttf",   r"C:\Windows\Fonts\arialbd.ttf"),
    ("DejaVu",     r"C:\Windows\Fonts\DejaVuSans.ttf", r"C:\Windows\Fonts\DejaVuSans-Bold.ttf"),
]
_FONT_NAME = "Helvetica"       # fallback без кириллицы
_FONT_BOLD = "Helvetica-Bold"
_FONTS_REGISTERED = False


def _register_fonts():
    global _FONT_NAME, _FONT_BOLD, _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for name, regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular):
            pdfmetrics.registerFont(TTFont(name, regular))
            if os.path.exists(bold):
                pdfmetrics.registerFont(TTFont(f"{name}-Bold", bold))
                _FONT_BOLD = f"{name}-Bold"
            else:
                _FONT_BOLD = name
            _FONT_NAME = name
            break

    _FONTS_REGISTERED = True


# ── Цвета ─────────────────────────────────────────────────────────────────────
from reportlab.lib import colors

_COLOR_PRIMARY   = colors.HexColor("#2563EB")   # синий заголовок
_COLOR_ACCENT    = colors.HexColor("#F3F4F6")   # светло-серый фон строк таблицы
_COLOR_HEADER    = colors.HexColor("#1E3A5F")   # тёмно-синий шапка таблицы
_COLOR_TOTAL     = colors.HexColor("#EFF6FF")   # голубой итог

_CATEGORY_EMOJI = {
    "Рестораны и еда": "🍕",
    "Транспорт":       "🚗",
    "Жилье":           "🏠",
    "Одежда":          "👕",
    "Быт":             "🏡",
    "Техника":         "💻",
    "Образование":     "📚",
    "Развлечения":     "🎬",
    "Здоровье":        "💊",
}

_MONTH_RU = [
    "", "январе", "феврале", "марте", "апреле", "мае", "июне",
    "июле", "августе", "сентябре", "октябре", "ноябре", "декабре",
]
_MONTH_RU_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def generate_monthly_report(
    expenses: list[tuple],   # (amount, description, created_at, category_name)
    username: str,
    year: int | None = None,
    month: int | None = None,
) -> bytes:
    """
    Генерирует PDF-отчёт за указанный месяц (по умолчанию — текущий).
    Возвращает байты PDF.
    """
    _register_fonts()

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    now = datetime.now()
    year  = year  or now.year
    month = month or now.month

    # Фильтруем расходы по нужному месяцу
    rows = [
        (amount, desc, created_at, cat)
        for amount, desc, created_at, cat in expenses
        if created_at.year == year and created_at.month == month
    ]

    # ── Стили ─────────────────────────────────────────────────────────────────
    def _style(name, **kw):
        kw.setdefault("fontName", _FONT_NAME)
        return ParagraphStyle(name, **kw)

    style_title   = _style("Title",   fontSize=22, textColor=_COLOR_PRIMARY,
                           spaceAfter=4, fontName=_FONT_BOLD, alignment=TA_CENTER)
    style_sub     = _style("Sub",     fontSize=11, textColor=colors.grey,
                           spaceAfter=2, alignment=TA_CENTER)
    style_section = _style("Section", fontSize=13, textColor=_COLOR_HEADER,
                           spaceBefore=12, spaceAfter=4, fontName=_FONT_BOLD)
    style_body    = _style("Body",    fontSize=9,  leading=13)
    style_small   = _style("Small",   fontSize=8,  textColor=colors.grey)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm,  bottomMargin=2 * cm,
        title=f"Отчёт за {_MONTH_RU[month]} {year}",
        author="AllocationBot",
    )

    story = []

    # ── Заголовок ──────────────────────────────────────────────────────────────
    story.append(Paragraph("💰 Финансовый отчёт", style_title))
    story.append(Paragraph(
        f"за {_MONTH_RU[month]} {year}  •  @{username}",
        style_sub,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=_COLOR_PRIMARY, spaceAfter=10))

    if not rows:
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph("За этот период расходов не найдено.", style_body))
        doc.build(story)
        return buf.getvalue()

    # ── Считаем статистику ────────────────────────────────────────────────────
    total = sum(float(r[0]) for r in rows if r[0])
    by_cat: dict[str, float] = defaultdict(float)
    for amount, _, _, cat in rows:
        by_cat[cat or "Прочее"] += float(amount) if amount else 0.0
    by_cat_sorted = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)

    # Блок сводки
    story.append(Paragraph("Сводка", style_section))

    summary_data = [
        ["Показатель", "Значение"],
        ["Всего трат",         f"{len(rows)}"],
        ["Общая сумма",        f"{total:.2f} BYN"],
        ["Средняя трата",      f"{total / len(rows):.2f} BYN"],
        ["Топ-категория",      f"{by_cat_sorted[0][0]} — {by_cat_sorted[0][1]:.2f} BYN"],
    ]
    summary_table = Table(summary_data, colWidths=[9 * cm, 8 * cm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (-1, 0),  _FONT_BOLD),
        ("FONTNAME",     (0, 1), (-1, -1), _FONT_NAME),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("BACKGROUND",   (0, 0), (-1, 0),  _COLOR_HEADER),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_ACCENT]),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(summary_table)

    # ── По категориям ──────────────────────────────────────────────────────────
    story.append(Paragraph("Расходы по категориям", style_section))

    cat_data = [["Категория", "Сумма, BYN", "% от итога"]]
    for cat, amt in by_cat_sorted:
        emoji = _CATEGORY_EMOJI.get(cat, "•")
        pct = (amt / total * 100) if total else 0
        cat_data.append([f"{emoji}  {cat}", f"{amt:.2f}", f"{pct:.1f}%"])
    cat_data.append(["Итого", f"{total:.2f}", "100%"])

    col_w = [10 * cm, 4 * cm, 3 * cm]
    cat_table = Table(cat_data, colWidths=col_w)
    cat_style = [
        ("FONTNAME",      (0, 0),  (-1, 0),   _FONT_BOLD),
        ("FONTNAME",      (0, 1),  (-1, -2),  _FONT_NAME),
        ("FONTNAME",      (0, -1), (-1, -1),  _FONT_BOLD),
        ("FONTSIZE",      (0, 0),  (-1, -1),  9),
        ("BACKGROUND",    (0, 0),  (-1, 0),   _COLOR_HEADER),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),   colors.white),
        ("BACKGROUND",    (0, -1), (-1, -1),  _COLOR_TOTAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2),  [colors.white, _COLOR_ACCENT]),
        ("ALIGN",         (1, 0),  (-1, -1),  "RIGHT"),
        ("GRID",          (0, 0),  (-1, -1),  0.3, colors.lightgrey),
        ("LEFTPADDING",   (0, 0),  (-1, -1),  8),
        ("RIGHTPADDING",  (0, 0),  (-1, -1),  8),
        ("TOPPADDING",    (0, 0),  (-1, -1),  5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1),  5),
    ]
    cat_table.setStyle(TableStyle(cat_style))
    story.append(cat_table)

    # ── Детализация ────────────────────────────────────────────────────────────
    story.append(Paragraph("Все расходы", style_section))

    detail_data = [["Дата", "Категория", "Описание", "Сумма"]]
    for amount, desc, created_at, cat in sorted(rows, key=lambda r: r[2]):
        date_str = created_at.strftime("%d.%m")
        cat_short = (cat or "—")[:16]
        desc_short = (desc or "—")[:40]
        amt_str = f"{float(amount):.2f}" if amount else "—"
        detail_data.append([date_str, cat_short, desc_short, amt_str])

    detail_table = Table(
        detail_data,
        colWidths=[1.8 * cm, 4.5 * cm, 8.5 * cm, 2.5 * cm],
        repeatRows=1,
    )
    detail_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0),  (-1, 0),  _FONT_BOLD),
        ("FONTNAME",      (0, 1),  (-1, -1), _FONT_NAME),
        ("FONTSIZE",      (0, 0),  (-1, -1), 8),
        ("BACKGROUND",    (0, 0),  (-1, 0),  _COLOR_HEADER),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_ACCENT]),
        ("ALIGN",         (3, 0),  (3, -1),  "RIGHT"),
        ("GRID",          (0, 0),  (-1, -1), 0.3, colors.lightgrey),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 6),
        ("TOPPADDING",    (0, 0),  (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 4),
        ("WORDWRAP",      (2, 1),  (2, -1),  True),
    ]))
    story.append(detail_table)

    # ── Футер ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Paragraph(
        f"Сформировано {now.strftime('%d.%m.%Y %H:%M')} · AllocationBot",
        style_small,
    ))

    doc.build(story)
    return buf.getvalue()
