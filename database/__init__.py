from database.user_repository import UserRepository
from database.expense_repository import ExpenseRepository
from database.reminder_repository import ReminderRepository
from database.model_repository import ModelRepository
from database.challenge_repository import ChallengeRepository
from database.pet_repository import PetRepository

users: UserRepository | None = None
expenses: ExpenseRepository | None = None
reminders: ReminderRepository | None = None
models: ModelRepository | None = None
challenges: ChallengeRepository | None = None
pet: PetRepository | None = None


def init(pool) -> None:
    global users, expenses, reminders, models, challenges, pet
    users = UserRepository(pool)
    expenses = ExpenseRepository(pool)
    reminders = ReminderRepository(pool)
    models = ModelRepository(pool)
    challenges = ChallengeRepository(pool)
    pet = PetRepository(pool)
