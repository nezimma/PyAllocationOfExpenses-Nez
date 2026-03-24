# tensorboard_utils/tensorboard_logger.py — визуализация обучения и эмбеддингов
import io
import os
import logging
import datetime
import tensorflow as tf
from tensorboard.plugins import projector

logger = logging.getLogger(__name__)


class TensorBoardLogger:
    """Настраивает TensorBoard callbacks и сохраняет эмбеддинги для Projector."""

    def __init__(self, log_base_dir: str = "logs"):
        self.fit_log_dir = os.path.join(log_base_dir, "fit")
        self.projector_log_dir = os.path.join(log_base_dir, "projector")
        os.makedirs(self.fit_log_dir, exist_ok=True)
        os.makedirs(self.projector_log_dir, exist_ok=True)

    def get_callback(self) -> tf.keras.callbacks.TensorBoard:
        """Возвращает TensorBoard callback для передачи в model.fit()."""
        return tf.keras.callbacks.TensorBoard(
            log_dir=self.fit_log_dir,
            histogram_freq=1,
            write_graph=True,
            write_images=True,
        )

    def save_embeddings(self, model: tf.keras.Model, vectorize_layer):
        """Сохраняет веса эмбеддинг-слоя и словарь для TensorBoard Projector."""
        embedding_layer = model.layers[0]
        weights = embedding_layer.get_weights()[0]
        vocab = vectorize_layer.get_vocabulary()

        # Обрезаем до размера словаря
        weights = weights[: len(vocab) - 1, :]

        embedding_var = tf.Variable(weights, name="word_embedding")
        checkpoint = tf.train.Checkpoint(embedding=embedding_var)
        checkpoint.save(os.path.join(self.projector_log_dir, "embedding.ckpt"))

        metadata_path = os.path.join(self.projector_log_dir, "metadata.tsv")
        with io.open(metadata_path, "w", encoding="utf-8") as f:
            for word in vocab:
                f.write(f"{word}\n")

        config = projector.ProjectorConfig()
        embedding_cfg = config.embeddings.add()
        embedding_cfg.tensor_name = "word_embedding:0"
        embedding_cfg.metadata_path = "metadata.tsv"
        projector.visualize_embeddings(self.projector_log_dir, config)

        logger.info(f"Embedding shape: {weights.shape}, vocab size: {len(vocab)}")
        logger.info(f"Projector logs saved to: {self.projector_log_dir}")
        logger.info(f"Fit logs saved to: {self.fit_log_dir}")
