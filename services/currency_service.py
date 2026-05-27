# services/currency_service.py — курсы валют через бесплатный API Нацбанка РБ
import time
import logging
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

_NBRB_URL = "https://api.nbrb.by/exrates/rates?periodicity=0"

# Валюты, которые нас интересуют (аббревиатуры из NBRB)
SUPPORTED = {"USD", "EUR", "RUB", "PLN", "GBP", "CNY", "UAH"}

_cache: dict[str, float] = {}   # {"USD": 3.2540, ...} — всё в BYN
_cache_ts: float = 0.0
_CACHE_TTL = 3600  # 1 час

# Символы для отображения
CURRENCY_SYMBOLS: dict[str, str] = {
    "BYN": "Br",
    "USD": "$",
    "EUR": "€",
    "RUB": "₽",
    "PLN": "zł",
    "GBP": "£",
    "CNY": "¥",
    "UAH": "₴",
}

# Часовой пояс → предпочтительная валюта
TZ_TO_CURRENCY: dict[str, str] = {
    "Europe/Minsk":  "BYN",
    "Europe/Moscow": "RUB",
    "Europe/Samara": "RUB",
    "Europe/Saratov": "RUB",
    "Europe/Ulyanovsk": "RUB",
    "Europe/Volgograd": "RUB",
    "Europe/Kirov":  "RUB",
    "Europe/Astrakhan": "RUB",
    "Europe/Kaliningrad": "RUB",
    "Asia/Yekaterinburg": "RUB",
    "Asia/Omsk":     "RUB",
    "Asia/Novosibirsk": "RUB",
    "Asia/Tomsk":    "RUB",
    "Asia/Barnaul":  "RUB",
    "Asia/Novokuznetsk": "RUB",
    "Asia/Krasnoyarsk": "RUB",
    "Asia/Irkutsk":  "RUB",
    "Asia/Yakutsk":  "RUB",
    "Asia/Vladivostok": "RUB",
    "Asia/Ust-Nera": "RUB",
    "Asia/Magadan":  "RUB",
    "Asia/Sakhalin": "RUB",
    "Asia/Srednekolymsk": "RUB",
    "Asia/Kamchatka": "RUB",
    "Asia/Anadyr":   "RUB",
    "Europe/Kiev":   "UAH",
    "Europe/Kyiv":   "UAH",
    "Europe/Warsaw": "PLN",
    "Europe/London": "GBP",
    "Asia/Shanghai": "CNY",
    "Asia/Beijing":  "CNY",
}


def timezone_to_currency(tz_str: str) -> str:
    """Определяет валюту по строке часового пояса."""
    if tz_str in TZ_TO_CURRENCY:
        return TZ_TO_CURRENCY[tz_str]
    prefix = tz_str.split("/")[0] if "/" in tz_str else ""
    if prefix == "America":
        return "USD"
    if prefix == "Europe":
        return "EUR"
    return "BYN"


async def get_rates() -> dict[str, float]:
    """
    Возвращает курсы валют в BYN с кешем на 1 час.
    Формат: {"USD": 3.2540, "EUR": 3.5210, "RUB": 0.035, ...}
    """
    global _cache, _cache_ts

    if _cache and (time.time() - _cache_ts) < _CACHE_TTL:
        return dict(_cache)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(_NBRB_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning(f"NBRB API returned {resp.status}")
                    return dict(_cache) if _cache else {}
                data = await resp.json()

        rates: dict[str, float] = {}
        for item in data:
            abbr = item.get("Cur_Abbreviation", "")
            if abbr not in SUPPORTED:
                continue
            rate = float(item.get("Cur_OfficialRate", 0))
            scale = int(item.get("Cur_Scale", 1))
            if scale > 0 and rate > 0:
                rates[abbr] = rate / scale  # цена 1 единицы иностранной валюты в BYN

        _cache = rates
        _cache_ts = time.time()
        logger.info(f"Currency rates updated: {rates}")
        return dict(rates)

    except Exception as e:
        logger.error(f"Failed to fetch currency rates: {e}")
        return dict(_cache) if _cache else {}


def convert(amount: float, from_cur: str, to_cur: str, rates: dict[str, float]) -> float:
    """
    Конвертирует сумму из from_cur в to_cur.
    rates — словарь {валюта: курс_в_BYN}.
    """
    if from_cur == to_cur:
        return amount
    if from_cur == "BYN":
        rate_to = rates.get(to_cur)
        if not rate_to:
            return amount
        return amount / rate_to
    if to_cur == "BYN":
        rate_from = rates.get(from_cur)
        if not rate_from:
            return amount
        return amount * rate_from
    # Оба не BYN — через BYN как промежуточную
    rate_from = rates.get(from_cur)
    rate_to = rates.get(to_cur)
    if not rate_from or not rate_to:
        return amount
    return amount * rate_from / rate_to


def symbol(currency: str) -> str:
    return CURRENCY_SYMBOLS.get(currency, currency)
