# api/server.py — HTTP API для Telegram Mini App
import json
import logging
from aiohttp import web
from database import expenses as expense_repo
from database import reminders as reminder_repo
from services.notification_scheduler import _calc_next_fire
from datetime import time as dtime

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
        data = expense_repo.get_expenses_for_api(telegram_id)
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
        data = reminder_repo.get_reminders_for_api(telegram_id)
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
        reminder_id = reminder_repo.create_reminder_full(
            telegram_id, title, date_str, time_str, rtype, int(interval), end_date
        )
        h, m = map(int, time_str.split(":"))
        next_fire = _calc_next_fire(date_str.replace('-', '.'), dtime(h, m), rtype == 'habit', int(interval))
        if next_fire:
            reminder_repo.set_next_fire_at(reminder_id, next_fire)
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
        reminder_repo.update_reminder_full(
            reminder_id, title, date_str, time_str, rtype, int(interval), end_date
        )
        h, m = map(int, time_str.split(":"))
        next_fire = _calc_next_fire(date_str.replace('-', '.'), dtime(h, m), rtype == 'habit', int(interval))
        reminder_repo.set_next_fire_at(reminder_id, next_fire)
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
        reminder_repo.delete_reminder(reminder_id)
    except Exception as e:
        logger.error(f"delete_reminder error: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(status=200, text="OK"))


async def handle_toggle_reminder(request: web.Request) -> web.Response:
    try:
        reminder_id = int(request.match_info["reminder_id"])
    except ValueError:
        return _cors(web.Response(status=400, text="Invalid reminder_id"))

    try:
        new_active = reminder_repo.toggle_reminder_active(reminder_id)
    except Exception as e:
        logger.error(f"toggle_reminder error: {e}")
        return _cors(web.Response(status=500, text="DB error"))

    return _cors(web.Response(
        content_type="application/json",
        text=json.dumps({"active": new_active}),
    ))


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application()

    # Expenses
    app.router.add_route("OPTIONS", "/api/expenses/{telegram_id}", handle_options)
    app.router.add_get("/api/expenses/{telegram_id}", handle_expenses)

    # Reminders
    app.router.add_route("OPTIONS", "/api/reminders/{telegram_id}", handle_options)
    app.router.add_get("/api/reminders/{telegram_id}", handle_get_reminders)
    app.router.add_post("/api/reminders/{telegram_id}", handle_create_reminder)

    app.router.add_route("OPTIONS", "/api/reminders/{reminder_id}/toggle", handle_options)
    app.router.add_patch("/api/reminders/{reminder_id}/toggle", handle_toggle_reminder)

    app.router.add_route("OPTIONS", "/api/reminder/{reminder_id}", handle_options)
    app.router.add_put("/api/reminder/{reminder_id}", handle_update_reminder)
    app.router.add_delete("/api/reminder/{reminder_id}", handle_delete_reminder)

    return app
