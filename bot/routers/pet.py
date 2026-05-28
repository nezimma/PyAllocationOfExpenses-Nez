# bot/routers/pet.py — команда /pet
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

router = Router()

_PET_URL = "https://nezimma.github.io/PyAllocationOfExpenses-Nez/pet.html"


@router.message(F.text == "🪐 Питомец")
@router.message(Command("pet"))
async def cmd_pet(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🪐 Открыть питомца",
            web_app=WebAppInfo(url=_PET_URL),
        )
    ]])
    await message.answer(
        "🪐 <b>Твой финансовый пришелец</b>\n\n"
        "Он растёт вместе с тобой — чем больше записываешь и выполняешь вызовы, "
        "тем сильнее становится.\n\n"
        "Не забывай кормить его хотя бы 4 раза в неделю! 👾",
        parse_mode="HTML",
        reply_markup=kb,
    )
