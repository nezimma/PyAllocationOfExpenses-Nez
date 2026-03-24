#!/usr/bin/env python3
# main.py — точка входа в приложение
"""
Запуск:
    python main.py

Переменные окружения (или .env):
    BOT_TOKEN           — токен Telegram-бота
    YANDEX_DISK_TOKEN   — OAuth-токен Яндекс.Диска
    DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT
"""
import asyncio
import logging
from bot import run

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run())
