#!/usr/bin/env python3
# train.py — скрипт обучения модели (запускается отдельно от бота)
"""
Запуск:
    python train.py [--dataset DatasetK.csv]

Флаги:
    --dataset   путь к CSV-файлу датасета (по умолчанию DatasetK.csv)
    --tb        включить TensorBoard-логирование
"""
import argparse
import logging
from database import models as model_repo
from ml.model_service import ExpenseModelService
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Train expense classifier")
    parser.add_argument("--dataset", default="DatasetK.csv", help="Path to CSV dataset")
    parser.add_argument("--tb", action="store_true", help="Enable TensorBoard logging")
    args = parser.parse_args()

    model_repo.init_table()
    svc = ExpenseModelService(cfg=config.model, model_repo=model_repo)

    if args.tb:
        from tensorboard_utils import TensorBoardLogger
        tb = TensorBoardLogger()
        logger.info(f"TensorBoard logs: {tb.fit_log_dir}")
        logger.info("Start TensorBoard with: tensorboard --logdir logs")

    logger.info(f"Training with dataset: {args.dataset}")
    svc.train_and_save(dataset_csv=args.dataset)
    logger.info("Training complete. Model saved.")


if __name__ == "__main__":
    main()
