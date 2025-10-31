from tensorboard.plugins import projector
import io
import os
import tensorflow as tf
import Learning_model
import datetime
import shutil

# === 1. Настройка путей ===
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

fit_log_dir = os.path.join("logs", "fit")
os.makedirs(fit_log_dir, exist_ok=True)

projector_log_dir = os.path.join("logs", "projector")
os.makedirs(projector_log_dir, exist_ok=True)

# === 2. TensorBoard callback ===
tensorboard_callback = tf.keras.callbacks.TensorBoard(
    log_dir=fit_log_dir,
    histogram_freq=1,
    write_graph=True,
    write_images=True
)

# === 3. Обучение модели ===
history = Learning_model.model.fit(
    Learning_model.train_ds,
    validation_data=Learning_model.val_ds,
    epochs=Learning_model.epochs,
    callbacks=[tensorboard_callback, Learning_model.early_stopping]
)

# === 4. Извлекаем веса и словарь ===
embedding_layer = Learning_model.model.layers[0]
embedding_weights = embedding_layer.get_weights()[0]
vocab = Learning_model.vectorize_layer.get_vocabulary()

# Приводим размеры к совпадению
embedding_weights = embedding_weights[:len(vocab)-1, :]

# === 5. Сохраняем веса для Projector ===
embedding_var = tf.Variable(embedding_weights)
checkpoint = tf.train.Checkpoint(embedding=embedding_var)
checkpoint.save(os.path.join(projector_log_dir, "embedding.ckpt"))

# === 6. Сохраняем метаданные ===
metadata_file = os.path.join(projector_log_dir, "metadata.tsv")
with io.open(metadata_file, "w", encoding="utf-8") as f:
    for word in vocab:
        f.write(f"{word}\n")

# === 7. Конфигурация для Projector ===
config = projector.ProjectorConfig()
embedding = config.embeddings.add()
embedding.tensor_name = "word_embedding:0"  # имя переменной без ":0"
embedding.metadata_path = "metadata.tsv"
projector.visualize_embeddings(projector_log_dir, config)

# === 8. Проверка ===
print("Embedding shape:", embedding_weights.shape)
print("Vocab length:", len(vocab))
print(f"Logs saved to: {projector_log_dir}")
print(f"TensorBoard fit logs: {fit_log_dir}")
