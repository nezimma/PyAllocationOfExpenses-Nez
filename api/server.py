# api/server.py — HTTP API для Telegram Mini App
import json
import logging
from aiohttp import web
from database import expenses as expense_repo

logger = logging.getLogger(__name__)


def _cors(response: web.Response) -> web.Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


async def handle_options(request: web.Request) -> web.Response:
    return _cors(web.Response(status=204))


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


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_route("OPTIONS", "/api/expenses/{telegram_id}", handle_options)
    app.router.add_get("/api/expenses/{telegram_id}", handle_expenses)
    return app
