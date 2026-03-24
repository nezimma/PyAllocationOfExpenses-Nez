# ml/model_service.py — обучение, сохранение, загрузка и предсказания ML-модели
import os
import logging
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, losses

logger = logging.getLogger(__name__)

CATEGORIES = {0: "Рестораны и еда", 1: "Транспорт"}
STOP_CHARS = list(',.*-–()[]{}!&"\'#№:;—«»?')


class ExpenseModelService:
    """Сервис для классификации трат по категориям."""

    def __init__(self, cfg, model_repo):
        self.cfg = cfg
        self.model_repo = model_repo
        self._model = None

    # ─── Public API ──────────────────────────────────────────────

    def predict_category(self, text: str) -> str:
        if self._model is None:
            raise RuntimeError("Model is not loaded. Call load_latest() first.")
        input_tensor = tf.constant([text])
        prediction = self._model.predict(input_tensor, verbose=0)[0][0]
        return CATEGORIES[0] if prediction <= 0.5 else CATEGORIES[1]

    def load_latest(self) -> bool:
        """Загружает последнюю версию модели из директории version_dir."""
        row = self.model_repo.get_latest(self.cfg.name)
        if not row:
            logger.warning("No saved model found in DB")
            return False
        version_dir, version = row
        model_path = os.path.join(version_dir, "model.keras")
        vocab_path = os.path.join(version_dir, "vocab.txt")

        if not os.path.exists(model_path):
            logger.warning(f"Model file missing: {model_path}")
            return False
        if not os.path.exists(vocab_path):
            logger.warning(f"Vocab file missing: {vocab_path}")
            return False

        inner_model = tf.keras.models.load_model(model_path)

        with open(vocab_path, encoding="utf-8") as f:
            vocab = f.read().splitlines()

        vectorize_layer = layers.TextVectorization(
            max_tokens=self.cfg.max_features,
            output_mode="int",
            output_sequence_length=self.cfg.sequence_length,
        )
        vectorize_layer.set_vocabulary(vocab)

        self._model = tf.keras.Sequential([vectorize_layer, inner_model])
        self._model.compile(
            loss=losses.BinaryCrossentropy(from_logits=False),
            optimizer="adam", metrics=["accuracy"]
        )
        logger.info(f"Loaded model v{version} from {version_dir}")
        return True

    def train_and_save(self, dataset_csv: str | None = None):
        """Обучает модель и сохраняет её в файловую систему и БД."""
        if dataset_csv:
            self._prepare_dataset(dataset_csv)

        train_ds, val_ds = self._load_split("train")
        test_ds = self._load_split("test")

        vectorize_layer = self._build_vectorizer(train_ds)
        model = self._build_model(vectorize_layer)
        model, history = self._train(model, train_ds, val_ds, vectorize_layer)

        export_model = self._export(model, vectorize_layer)
        self._log_results(export_model, test_ds, history)

        self._persist(export_model)
        self._model = export_model

    # ─── Private helpers ─────────────────────────────────────────

    def _prepare_dataset(self, csv_path: str):
        df = pd.read_csv(csv_path, sep="|")
        os.makedirs(os.path.join(self.cfg.train_dir, "Restaurans_food"), exist_ok=True)
        os.makedirs(os.path.join(self.cfg.train_dir, "Transport"), exist_ok=True)
        i = j = 1
        for _, row in df.iterrows():
            clean = str(row["data"])
            for ch in STOP_CHARS:
                clean = clean.replace(ch, "")
            category = str(row["category"])
            if category == "Ресторан и еда":
                path = os.path.join(self.cfg.train_dir, "Restaurans_food", f"a_text_{i}.txt")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(clean)
                i += 1
            elif category == "Транспорт":
                path = os.path.join(self.cfg.train_dir, "Transport", f"b_text_{j}.txt")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(clean)
                j += 1

    def _load_split(self, mode: str):
        if mode == "train":
            train_ds = tf.keras.utils.text_dataset_from_directory(
                self.cfg.train_dir, batch_size=self.cfg.batch_size,
                validation_split=0.2, subset="training", seed=self.cfg.seed
            )
            val_ds = tf.keras.utils.text_dataset_from_directory(
                self.cfg.train_dir, batch_size=self.cfg.batch_size,
                validation_split=0.2, subset="validation", seed=self.cfg.seed
            )
            return train_ds, val_ds
        else:
            return tf.keras.utils.text_dataset_from_directory(
                self.cfg.test_dir, batch_size=self.cfg.batch_size
            )

    def _build_vectorizer(self, train_ds):
        vectorize_layer = layers.TextVectorization(
            max_tokens=self.cfg.max_features,
            output_mode="int",
            output_sequence_length=self.cfg.sequence_length,
        )
        vectorize_layer.adapt(train_ds.map(lambda x, y: x))
        return vectorize_layer

    def _build_model(self, vectorize_layer):
        vocab_size = len(vectorize_layer.get_vocabulary())
        model = tf.keras.Sequential([
            layers.Embedding(input_dim=vocab_size, output_dim=self.cfg.embedding_dim),
            layers.Conv1D(128, 5, activation="relu", padding="same"),
            layers.BatchNormalization(),
            layers.GlobalMaxPooling1D(),
            layers.Dropout(0.5),
            layers.Dense(64, activation="relu"),
            layers.Dropout(0.5),
            layers.Dense(1, activation="sigmoid"),
        ])
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
            loss=losses.BinaryCrossentropy(),
            metrics=[
                tf.keras.metrics.BinaryAccuracy(threshold=0.5),
                tf.keras.metrics.Precision(),
                tf.keras.metrics.Recall(),
            ],
        )
        return model

    def _train(self, model, train_ds, val_ds, vectorize_layer):
        AUTOTUNE = tf.data.AUTOTUNE

        def vectorize(text, label):
            return vectorize_layer(tf.expand_dims(text, -1)), label

        train_ds = train_ds.map(vectorize).cache().prefetch(AUTOTUNE)
        val_ds = val_ds.map(vectorize).cache().prefetch(AUTOTUNE)

        early_stop = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=3, restore_best_weights=True
        )
        history = model.fit(
            train_ds, validation_data=val_ds,
            epochs=self.cfg.epochs, callbacks=[early_stop]
        )
        return model, history

    def _export(self, model, vectorize_layer):
        """Собирает export_model для eval/predict. Сохраняем слои раздельно."""
        export = tf.keras.Sequential([vectorize_layer, model])
        export.compile(
            loss=losses.BinaryCrossentropy(from_logits=False),
            optimizer="adam", metrics=["accuracy"]
        )
        return export

    def _log_results(self, export_model, test_ds, history):
        loss, accuracy = export_model.evaluate(test_ds)
        logger.info(f"Test loss: {loss:.4f}, accuracy: {accuracy:.4f}")

    def _persist(self, export_model):
        """Сохраняет модель и словарь раздельно.

        Обходит UnicodeEncodeError (cp1251) на Windows: Keras пишет
        русский словарь внутрь .keras-архива через системную кодировку.
        Разделяем:
          models/expense_model_v1/
            model.keras   -- только веса/архитектура (ASCII-safe)
            vocab.txt     -- словарь UTF-8
        """
        os.makedirs(self.cfg.dir, exist_ok=True)
        row = self.model_repo.get_latest(self.cfg.name)
        version = (row[1] + 1) if row else 1

        version_dir = os.path.join(self.cfg.dir, f"{self.cfg.name}_v{version}")
        os.makedirs(version_dir, exist_ok=True)

        # layers[0] = vectorize_layer, layers[1] = основная модель
        vectorize_layer = export_model.layers[0]
        inner_model = export_model.layers[1]

        model_path = os.path.join(version_dir, "model.keras")
        inner_model.save(model_path)

        vocab_path = os.path.join(version_dir, "vocab.txt")
        vocab = vectorize_layer.get_vocabulary()
        with open(vocab_path, "w", encoding="utf-8") as f:
            f.write("\n".join(vocab))

        self.model_repo.save_metadata(self.cfg.name, version_dir, version)
        logger.info(f"Model v{version} saved to {version_dir}")
