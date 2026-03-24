# ml/__init__.py
from config import config
from database import models as model_repo
from ml.model_service import ExpenseModelService

model_svc = ExpenseModelService(cfg=config.model, model_repo=model_repo)
model_svc.load_latest()
