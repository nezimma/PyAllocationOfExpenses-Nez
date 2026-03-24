# database/__init__.py
from config import config
from database.db import PostgresConnection
from database.user_repository import UserRepository
from database.expense_repository import ExpenseRepository
from database.reminder_repository import ReminderRepository
from database.model_repository import ModelRepository

_db = PostgresConnection(
    host=config.database.host,
    user=config.database.user,
    password=config.database.password,
    db_name=config.database.db_name,
    port=config.database.port,
)

users = UserRepository(_db)
expenses = ExpenseRepository(_db)
reminders = ReminderRepository(_db)
models = ModelRepository(_db)
