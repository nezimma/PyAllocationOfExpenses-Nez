# ml/__init__.py
from config import config
from ml.model_service import ExpenseModelService

# model_repo передаётся снаружи — после инициализации пула БД (database.init).
# train.py использует FileModelRepository; бот вызывает init_model_svc() после database.init().
model_svc: ExpenseModelService | None = None


def init_model_svc(model_repo) -> None:
    """Вызывается из bot/__init__.py после database.init(pool)."""
    global model_svc
    model_svc = ExpenseModelService(cfg=config.model, model_repo=model_repo)
