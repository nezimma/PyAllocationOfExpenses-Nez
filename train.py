#!/usr/bin/env python3
# train.py — одноразовый скрипт для обучения/переобучения модели
# Запуск: python train.py
# Не требует БД — метаданные хранятся в models/model_meta.json
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

DATASET_CSV = os.path.join(os.path.dirname(__file__), "DatasetK.csv")

if not os.path.exists(DATASET_CSV):
    raise FileNotFoundError(f"Датасет не найден: {DATASET_CSV}")

from config import config
from ml.model_service import ExpenseModelService
from ml.file_model_repository import FileModelRepository

# Синхронный файловый репо — не нужна БД
model_repo = FileModelRepository(models_dir=config.model.dir)
model_svc = ExpenseModelService(cfg=config.model, model_repo=model_repo)

print(f"Запускаем обучение на датасете: {DATASET_CSV}")
model_svc.train_and_save(dataset_csv=DATASET_CSV)
print("Готово! Теперь можно запускать main.py")
