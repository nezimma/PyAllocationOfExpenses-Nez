# ml/model_service.py — обучение, сохранение, загрузка и предсказания ML-модели
import os
import re
import shutil
import logging
import math
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, losses
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

STOP_CHARS = list(',.*-–()[]{}!&"\\#№:;—«»?')

SENTENCE_TRANSFORMER_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384  # выход paraphrase-multilingual-MiniLM-L12-v2

# Маппинг: название категории из CSV → имя папки (латиница, без пробелов)
CATEGORY_FOLDER_MAP = {
    "Ресторан и еда": "Restaurants_food",
    "Транспорт":      "Transport",
    "Жилье":          "Housing",
}


def _folder_name(category: str) -> str:
    """Возвращает имя папки для категории. Если нет в маппинге — транслитерирует."""
    if category in CATEGORY_FOLDER_MAP:
        return CATEGORY_FOLDER_MAP[category]
    safe = re.sub(r"[^\w]", "_", category.strip())
    return safe


def _count_files_in_dir(path: str) -> int:
    """Считает .txt файлы в папке (не рекурсивно)."""
    if not os.path.isdir(path):
        return 0
    return sum(1 for f in os.listdir(path) if f.endswith(".txt"))


def _clean_text(text: str) -> str:
    for ch in STOP_CHARS:
        text = text.replace(ch, "")
    return text.strip()


def _read_texts_and_labels(root_dir: str, categories: list[str]) -> tuple[list[str], list[int]]:
    """
    Читает все .txt файлы из подпапок root_dir.
    Возвращает (тексты, метки) где метка — индекс категории в отсортированном списке.
    """
    texts, labels = [], []
    cat_to_idx = {cat: idx for idx, cat in enumerate(categories)}

    for cat in categories:
        folder = _folder_name(cat)
        folder_path = os.path.join(root_dir, folder)
        if not os.path.isdir(folder_path):
            logger.warning(f"Папка не найдена: {folder_path}")
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".txt"):
                continue
            with open(os.path.join(folder_path, fname), encoding="utf-8") as f:
                texts.append(f.read().strip())
            labels.append(cat_to_idx[cat])

    return texts, labels


class ExpenseModelService:
    """Сервис для классификации трат по категориям."""

    def __init__(self, cfg, model_repo):
        self.cfg = cfg
        self.model_repo = model_repo
        self._model = None          # Keras Dense-классификатор
        self._encoder = None        # SentenceTransformer
        self._categories = None     # список категорий в алфавитном порядке

    # ─── Public API ──────────────────────────────────────────────

    def predict_category(self, text: str) -> str:
        if self._model is None or self._encoder is None:
            raise RuntimeError("Model is not loaded. Call load_latest() first.")
        embedding = self._encoder.encode([text], convert_to_numpy=True)  # (1, 384)
        probs = self._model.predict(embedding, verbose=0)[0]
        idx = int(np.argmax(probs))
        logger.debug(f"predict_category: text={text!r}, probs={probs}, idx={idx}, categories={self._categories}")
        if self._categories and idx < len(self._categories):
            return self._categories[idx]
        # Если labels не загружены — пытаемся подтянуть из БД
        row = self.model_repo.get_latest(self.cfg.name)
        if row:
            labels_path = os.path.join(row[0], "labels.txt")
            if os.path.exists(labels_path):
                with open(labels_path, encoding="utf-8") as f:
                    self._categories = f.read().splitlines()
                logger.warning("predict_category: _categories были None, загружены из labels.txt")
                if idx < len(self._categories):
                    return self._categories[idx]
        logger.error(f"predict_category: не удалось определить категорию для idx={idx}, categories={self._categories}")
        return "Неизвестная категория"

    def load_latest(self) -> bool:
        """Загружает последнюю версию модели из директории version_dir."""
        row = self.model_repo.get_latest(self.cfg.name)
        if not row:
            logger.warning("No saved model found in DB")
            return False
        version_dir, version = row
        model_path  = os.path.join(version_dir, "model.keras")
        labels_path = os.path.join(version_dir, "labels.txt")

        if not os.path.exists(model_path):
            logger.warning(f"Model file missing: {model_path}")
            return False

        self._model = tf.keras.models.load_model(model_path)

        # SentenceTransformer грузится из кеша (после первой загрузки — оффлайн)
        self._encoder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

        if os.path.exists(labels_path):
            with open(labels_path, encoding="utf-8") as f:
                self._categories = f.read().splitlines()
            logger.info(f"Loaded model v{version} from {version_dir}, categories: {self._categories}")
        else:
            logger.error(
                f"labels.txt NOT FOUND at {labels_path}! "
                "predict_category будет возвращать индекс вместо названия. "
                "Запустите train_and_save() заново."
            )

        logger.info(f"Loaded model v{version} from {version_dir}")
        return True

    def train_and_save(self, dataset_csv: str | None = None):
        """Проверяет актуальность папок, при необходимости пересобирает, затем обучает."""
        if dataset_csv:
            self._sync_dataset(dataset_csv)

        # Загружаем SentenceTransformer один раз — используется и при обучении, и при инференсе
        if self._encoder is None:
            logger.info(f"Загружаем SentenceTransformer: {SENTENCE_TRANSFORMER_MODEL}")
            self._encoder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

        # _categories должен быть заполнен в _sync_dataset; если нет — читаем из папок
        if self._categories:
            num_classes = len(self._categories)
        else:
            num_classes = self._detect_num_classes()
            logger.warning(
                f"_categories не заданы до обучения, num_classes определён как {num_classes} "
                "по папкам train_dir. Убедитесь, что dataset_csv передан в train_and_save()."
            )

        X_train, y_train, X_val, y_val, X_test, y_test = self._load_and_encode()

        model   = self._build_model(num_classes)
        model   = self._train(model, X_train, y_train, X_val, y_val)

        self._log_results(model, X_test, y_test)
        self._persist(model)
        self._model = model

    # ─── Dataset sync ────────────────────────────────────────────

    def _sync_dataset(self, csv_path: str):
        """
        Сравнивает количество строк в CSV с количеством файлов в папках.
        Если что-то не совпадает — полностью пересобирает train_dir и test_dir.
        Разбивка: 80% train, 20% test (детерминированная, без перемешивания).
        """
        df = pd.read_csv(csv_path, sep="|")
        df = df[df["data"].notna() & df["category"].notna()].copy()
        df["category"] = df["category"].str.strip()

        csv_counts = df["category"].value_counts().to_dict()
        self._categories = sorted(csv_counts.keys())

        needs_rebuild = False

        if not os.path.isdir(self.cfg.train_dir) or not os.path.isdir(self.cfg.test_dir):
            needs_rebuild = True
            logger.info("Папки датасета не найдены — собираем с нуля")
        else:
            for cat, csv_count in csv_counts.items():
                folder = _folder_name(cat)
                train_count = _count_files_in_dir(os.path.join(self.cfg.train_dir, folder))
                test_count  = _count_files_in_dir(os.path.join(self.cfg.test_dir,  folder))
                expected_train = math.floor(csv_count * 0.8)
                expected_test  = csv_count - expected_train

                if train_count != expected_train or test_count != expected_test:
                    logger.info(
                        f"[{cat}] CSV={csv_count} | "
                        f"train: есть {train_count}, ожидается {expected_train} | "
                        f"test: есть {test_count}, ожидается {expected_test} → пересборка"
                    )
                    needs_rebuild = True
                    break

        if not needs_rebuild:
            logger.info(
                f"Папки актуальны: {', '.join(f'{k}={v}' for k, v in csv_counts.items())}"
            )
            return

        logger.info("Пересобираем train_dir и test_dir...")
        if os.path.isdir(self.cfg.train_dir):
            shutil.rmtree(self.cfg.train_dir)
        if os.path.isdir(self.cfg.test_dir):
            shutil.rmtree(self.cfg.test_dir)

        for cat in self._categories:
            folder = _folder_name(cat)
            os.makedirs(os.path.join(self.cfg.train_dir, folder), exist_ok=True)
            os.makedirs(os.path.join(self.cfg.test_dir,  folder), exist_ok=True)

        for cat in self._categories:
            folder = _folder_name(cat)
            rows   = df[df["category"] == cat]["data"].tolist()
            split  = math.floor(len(rows) * 0.8)

            for i, text in enumerate(rows[:split], start=1):
                path = os.path.join(self.cfg.train_dir, folder, f"text_{i}.txt")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(_clean_text(str(text)))

            for i, text in enumerate(rows[split:], start=1):
                path = os.path.join(self.cfg.test_dir, folder, f"text_{i}.txt")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(_clean_text(str(text)))

            train_c = _count_files_in_dir(os.path.join(self.cfg.train_dir, folder))
            test_c  = _count_files_in_dir(os.path.join(self.cfg.test_dir,  folder))
            logger.info(f"[{cat}] → {folder}: train={train_c}, test={test_c}")

        logger.info("Датасет пересобран успешно")

    def _detect_num_classes(self) -> int:
        if not os.path.isdir(self.cfg.train_dir):
            return 2
        return len([
            d for d in os.listdir(self.cfg.train_dir)
            if os.path.isdir(os.path.join(self.cfg.train_dir, d))
        ])

    # ─── Encode + Split ──────────────────────────────────────────

    def _load_and_encode(self):
        """
        Читает тексты из train_dir и test_dir, кодирует через SentenceTransformer.
        Из train делает дополнительный val-сплит (80/20).
        Возвращает: X_train, y_train, X_val, y_val, X_test, y_test (numpy arrays).
        """
        train_texts, train_labels = _read_texts_and_labels(self.cfg.train_dir, self._categories)
        test_texts,  test_labels  = _read_texts_and_labels(self.cfg.test_dir,  self._categories)

        logger.info(f"Кодируем {len(train_texts)} train-текстов...")
        X_all = self._encoder.encode(train_texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
        y_all = np.array(train_labels)

        # Детерминированный val-сплит (последние 20%)
        split = math.floor(len(X_all) * 0.8)
        X_train, y_train = X_all[:split], y_all[:split]
        X_val,   y_val   = X_all[split:], y_all[split:]

        logger.info(f"Кодируем {len(test_texts)} test-текстов...")
        X_test = self._encoder.encode(test_texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
        y_test = np.array(test_labels)

        logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
        return X_train, y_train, X_val, y_val, X_test, y_test

    # ─── Model build / train ─────────────────────────────────────

    def _build_model(self, num_classes: int):
        """
        Простой Dense-классификатор поверх готовых эмбеддингов (384-мерный вход).
        SentenceTransformer здесь не входит в граф — он используется отдельно для encode().
        """
        model = tf.keras.Sequential([
            layers.Input(shape=(EMBEDDING_DIM,)),
            layers.Dense(64, activation="relu"),
            layers.Dropout(0.3),
            layers.Dense(num_classes, activation="softmax"),
        ])
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
            loss=losses.SparseCategoricalCrossentropy(),
            metrics=[
                tf.keras.metrics.SparseCategoricalAccuracy(),
                tf.keras.metrics.SparseTopKCategoricalAccuracy(k=2, name="top2_acc"),
            ],
        )
        return model

    def _train(self, model, X_train, y_train, X_val, y_val):
        early_stop = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=5, restore_best_weights=True
        )
        model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=self.cfg.epochs,
            batch_size=self.cfg.batch_size,
            callbacks=[early_stop],
        )
        return model

    def _log_results(self, model, X_test, y_test):
        loss, accuracy, top2 = model.evaluate(X_test, y_test, verbose=0)
        logger.info(f"Test loss: {loss:.4f}, accuracy: {accuracy:.4f}, top2: {top2:.4f}")

    # ─── Persist ─────────────────────────────────────────────────

    def _persist(self, model):
        """Сохраняет model.keras и labels.txt. vocab.txt больше не нужен."""
        os.makedirs(self.cfg.dir, exist_ok=True)
        row = self.model_repo.get_latest(self.cfg.name)
        version = (row[1] + 1) if row else 1

        version_dir = os.path.join(self.cfg.dir, f"{self.cfg.name}_v{version}")
        os.makedirs(version_dir, exist_ok=True)

        model.save(os.path.join(version_dir, "model.keras"))

        if self._categories:
            with open(os.path.join(version_dir, "labels.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(self._categories))

        self.model_repo.save_metadata(self.cfg.name, version_dir, version)
        logger.info(f"Model v{version} saved to {version_dir}")