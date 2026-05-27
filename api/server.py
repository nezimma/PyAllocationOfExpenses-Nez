import json
import logging
from datetime import date, time as dtime
from aiohttp import web
import database
from services.scheduler_utils import calc_next_fire, get_tz
from services import currency_service
from services import forecast_service

logger = logging.getLogger(__name__)

_ALLOW_METHODS = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
_ALLOW_HEADERS = "Content-Type, ngrok-skip-browser-warning"


def _cors(response: web.Response) -> web.Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = _ALLOW_METHODS
    response.headers["Access-Control-Allow-Headers"] = _ALLOW_HEADERS
    return response


async def handle_options(request: web.Request) -> web.Response:
    return _cors(web.Response(status=204))


# ── Expenses ──────────────────────────────────────────────────────────────────

async def handle_expenses(request: web.Request) -> web.Response:
    try:
        telegram_id = int(request.match_info["telegram_id"])
    except ValueError:
        return web.Response(status=400, text="Invalid telegram_id")

    try:
        data = await database.expenses.get_expenses_for_api(telegram_id)
    except Exception as e:
        logger.error(f"DB error for telegram_id={telegram_id}: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(
        content_type="application/json",
        text=json.dumps(data, ensure_ascii=False),
    ))


# ── Reminders ─────────────────────────────────────────────────────────────────

async def handle_get_reminders(request: web.Request) -> web.Response:
    try:
        telegram_id = int(request.match_info["telegram_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid telegram_id"))

    try:
        data = await database.reminders.get_reminders_for_api(telegram_id)
    except Exception as e:
        logger.error(f"get_reminders error telegram_id={telegram_id}: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(
        content_type="application/json",
        text=json.dumps(data, ensure_ascii=False, default=str),
    ))


async def handle_create_reminder(request: web.Request) -> web.Response:
    try:
        telegram_id = int(request.match_info["telegram_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid telegram_id"))

    try:
        body = await request.json()
    except Exception:
        return _cors(web.Response(status=400, text="Invalid JSON"))

    title    = body.get("title", "").strip()
    date_str = body.get("date", "")
    time_str = body.get("time", "")
    rtype    = body.get("type", "reminder")
    interval = body.get("interval") or 1
    end_date = body.get("endDate") or None

    if not title or not date_str or not time_str:
        return _cors(web.Response(status=400, text="title, date and time are required"))

    try:
        reminder_id = await database.reminders.create_reminder_full(
            telegram_id, title, date_str, time_str, rtype, int(interval), end_date
        )
        h, m = map(int, time_str.split(":"))
        tz = get_tz(await database.users.get_timezone(telegram_id))
        next_fire = calc_next_fire(date_str.replace("-", "."), dtime(h, m), rtype == "habit", int(interval), tz)
        if next_fire:
            await database.reminders.set_next_fire_at(reminder_id, next_fire)
    except Exception as e:
        logger.error(f"create_reminder error: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(
        status=201,
        content_type="application/json",
        text=json.dumps({"id": reminder_id}, ensure_ascii=False),
    ))


async def handle_update_reminder(request: web.Request) -> web.Response:
    try:
        reminder_id = int(request.match_info["reminder_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid reminder_id"))

    try:
        body = await request.json()
    except Exception:
        return _cors(web.Response(status=400, text="Invalid JSON"))

    title    = body.get("title", "").strip()
    date_str = body.get("date", "")
    time_str = body.get("time", "")
    rtype    = body.get("type", "reminder")
    interval = body.get("interval") or 1
    end_date = body.get("endDate") or None

    if not title or not date_str or not time_str:
        return _cors(web.Response(status=400, text="title, date and time are required"))

    try:
        await database.reminders.update_reminder_full(
            reminder_id, title, date_str, time_str, rtype, int(interval), end_date
        )
        h, m = map(int, time_str.split(":"))
        tg_id = await database.reminders.get_telegram_id_by_reminder(reminder_id)
        tz = get_tz(await database.users.get_timezone(tg_id)) if tg_id else None
        next_fire = calc_next_fire(date_str.replace("-", "."), dtime(h, m), rtype == "habit", int(interval), tz)
        await database.reminders.set_next_fire_at(reminder_id, next_fire)
    except Exception as e:
        logger.error(f"update_reminder error: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(status=200, text="OK"))


async def handle_delete_reminder(request: web.Request) -> web.Response:
    try:
        reminder_id = int(request.match_info["reminder_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid reminder_id"))

    try:
        await database.reminders.delete_reminder(reminder_id)
    except Exception as e:
        logger.error(f"delete_reminder error: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(status=200, text="OK"))


async def handle_checkin(request: web.Request) -> web.Response:
    try:
        reminder_id = int(request.match_info["reminder_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid reminder_id"))

    try:
        body = await request.json()
    except Exception:
        body = {}

    checkin_date = body.get("date") or date.today().isoformat()

    try:
        added = await database.reminders.add_checkin(reminder_id, checkin_date)
    except Exception as e:
        logger.error(f"checkin error: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(
        status=201 if added else 200,
        content_type="application/json",
        text=json.dumps({"date": checkin_date, "created": added}),
    ))


async def handle_toggle_reminder(request: web.Request) -> web.Response:
    try:
        reminder_id = int(request.match_info["reminder_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid reminder_id"))

    try:
        new_active = await database.reminders.toggle_reminder_active(reminder_id)
    except Exception as e:
        logger.error(f"toggle_reminder error: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(
        content_type="application/json",
        text=json.dumps({"active": new_active}),
    ))


# ── Expense CRUD ──────────────────────────────────────────────────────────────

async def handle_update_expense(request: web.Request) -> web.Response:
    try:
        expense_id = int(request.match_info["expense_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid expense_id"))

    try:
        body = await request.json()
        telegram_id = int(body["telegram_id"])
        ok = await database.expenses.update_expense(
            expense_id=expense_id,
            telegram_id=telegram_id,
            description=body.get("name", ""),
            amount=float(body.get("amount", 0)),
            currency=body.get("currency", "BYN"),
            category_key=body.get("cat", "other"),
            date_str=body.get("date", ""),
        )
        if not ok:
            return _cors(web.Response(status=404, text="Not found"))
        return _cors(web.Response(content_type="application/json", text='{"ok":true}'))
    except Exception as e:
        logger.error(f"handle_update_expense error: {e}")
        return _cors(web.Response(status=500, text=str(e)))


async def handle_delete_expense(request: web.Request) -> web.Response:
    try:
        expense_id = int(request.match_info["expense_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid expense_id"))

    try:
        body = await request.json()
        telegram_id = int(body["telegram_id"])
        ok = await database.expenses.delete_expense(expense_id, telegram_id)
        if not ok:
            return _cors(web.Response(status=404, text="Not found"))
        return _cors(web.Response(content_type="application/json", text='{"ok":true}'))
    except Exception as e:
        logger.error(f"handle_delete_expense error: {e}")
        return _cors(web.Response(status=500, text=str(e)))


# ── Budget forecast ───────────────────────────────────────────────────────────

async def handle_forecast(request: web.Request) -> web.Response:
    try:
        telegram_id = int(request.match_info["telegram_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid telegram_id"))

    try:
        from datetime import date as _date
        today = _date.today()
        year = int(request.rel_url.query.get("year", today.year))
        month = int(request.rel_url.query.get("month", today.month))

        rows = await database.expenses.get_monthly_daily_totals(telegram_id, year, month)

        # Конвертируем в BYN для унифицированного прогноза
        rates = await currency_service.get_rates()
        converted = [
            (day, currency_service.convert(amount, cur, "BYN", rates), category)
            for day, amount, cur, category in rows
        ]

        result = forecast_service.forecast_month(converted, year, month)
        return _cors(web.Response(
            content_type="application/json",
            text=json.dumps(result, ensure_ascii=False, default=str),
        ))
    except Exception as e:
        logger.error(f"handle_forecast error: {e}")
        return _cors(web.Response(status=500, text="forecast error"))


# ── Currency rates ────────────────────────────────────────────────────────────

async def handle_rates(request: web.Request) -> web.Response:
    try:
        rates = await currency_service.get_rates()
        payload = {
            "base": "BYN",
            "rates": rates,
            "symbols": currency_service.CURRENCY_SYMBOLS,
        }
        return _cors(web.Response(
            content_type="application/json",
            text=json.dumps(payload, ensure_ascii=False),
        ))
    except Exception as e:
        logger.error(f"handle_rates error: {e}")
        return _cors(web.Response(status=500, text="rates error"))


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application()

    app.router.add_route("OPTIONS", "/api/rates", handle_options)
    app.router.add_get("/api/rates", handle_rates)

    app.router.add_route("OPTIONS", "/api/forecast/{telegram_id}", handle_options)
    app.router.add_get("/api/forecast/{telegram_id}", handle_forecast)

    app.router.add_route("OPTIONS", "/api/expense/{expense_id}", handle_options)
    app.router.add_put("/api/expense/{expense_id}", handle_update_expense)
    app.router.add_delete("/api/expense/{expense_id}", handle_delete_expense)

    app.router.add_route("OPTIONS", "/api/expenses/{telegram_id}", handle_options)
    app.router.add_get("/api/expenses/{telegram_id}", handle_expenses)

    app.router.add_route("OPTIONS", "/api/reminders/{telegram_id}", handle_options)
    app.router.add_get("/api/reminders/{telegram_id}", handle_get_reminders)
    app.router.add_post("/api/reminders/{telegram_id}", handle_create_reminder)

    app.router.add_route("OPTIONS", "/api/reminders/{reminder_id}/toggle", handle_options)
    app.router.add_patch("/api/reminders/{reminder_id}/toggle", handle_toggle_reminder)

    app.router.add_route("OPTIONS", "/api/reminders/{reminder_id}/checkin", handle_options)
    app.router.add_post("/api/reminders/{reminder_id}/checkin", handle_checkin)

    app.router.add_route("OPTIONS", "/api/reminder/{reminder_id}", handle_options)
    app.router.add_put("/api/reminder/{reminder_id}", handle_update_reminder)
    app.router.add_delete("/api/reminder/{reminder_id}", handle_delete_reminder)

    return app
