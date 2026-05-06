#!/usr/bin/env python3
# train.py — одноразовый скрипт для обучения/переобучения модели
# Запуск: python train.py
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Путь к CSV относительно корня проекта
DATASET_CSV = os.path.join(os.path.dirname(__file__), "DatasetK.csv")

from ml import model_svc

if not os.path.exists(DATASET_CSV):
    raise FileNotFoundError(f"Датасет не найден: {DATASET_CSV}")

print(f"Запускаем обучение на датасете: {DATASET_CSV}")
model_svc.train_and_save(dataset_csv=DATASET_CSV)
print("Готово! Теперь можно запускать main.py")