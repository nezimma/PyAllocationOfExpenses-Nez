from database.user_repository import UserRepository
from database.expense_repository import ExpenseRepository
from database.reminder_repository import ReminderRepository
from database.model_repository import ModelRepository

users: UserRepository | None = None
expenses: ExpenseRepository | None = None
reminders: ReminderRepository | None = None
models: ModelRepository | None = None


def init(pool) -> None:
    global users, expenses, reminders, models
    users = UserRepository(pool)
    expenses = ExpenseRepository(pool)
    reminders = ReminderRepository(pool)
    models = ModelRepository(pool)
