import os
import tensorflow as tf
from tensorboard.plugins import projector
import re
import Learning_model
from tensorboard import program

# 1. Пути
log_dir = os.path.join(os.getcwd(), 'logs', 'imdb-example')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 2. Считываем слова из текстов
def read_words_from_file(filepath):
    words = set()
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            tokens = line.strip().split()
            for token in tokens:
                words.add(token)
    return words

train_dir = os.path.join(os.getcwd(), 'train_dir')
pattern = re.compile(r'.*_text_\d+\.txt')

all_words = set()
for root, dirs, files in os.walk(train_dir):
    for filename in files:
        if pattern.match(filename):
            file_path = os.path.join(root, filename)
            file_words = read_words_from_file(file_path)
            all_words.update(file_words)

# 3. Сохраняем слова в metadata.tsv
metadata_path = os.path.join(log_dir, 'metadata.tsv')
with open(metadata_path, 'w', encoding='utf-8') as f:
    for word in sorted(all_words):
        f.write(f"{word}\n")

# 4. Извлекаем веса из модели
embedding_weights = Learning_model.model.layers[0].get_weights()[0][1:]  # исключаем padding (0)
weights = tf.Variable(embedding_weights, name='embedding_weights')

# 5. Чекпоинт
checkpoint = tf.train.Checkpoint(embedding=weights)
checkpoint_path = os.path.join(log_dir, 'embedding.ckpt')
checkpoint.save(checkpoint_path)

# 6. Конфигурация projector
config = projector.ProjectorConfig()
embedding = config.embeddings.add()
embedding.tensor_name = weights.name.split(":")[0]
embedding.metadata_path = 'metadata.tsv'
projector.visualize_embeddings(log_dir, config)

print(embedding_weights.shape[0] == len(all_words))
print(len(all_words))  # должно быть равно embedding_weights.shape[0]
print(embedding_weights.shape)

print(f"Tensor name: {weights.name}")
print(f"Embedding shape: {embedding_weights.shape}")
print(f"Words in metadata: {len(all_words)}")
print(os.listdir(log_dir))

print(f"✔ TensorBoard project setup done. Logs saved to: {log_dir}")

# 7. Запуск TensorBoard из Python
tb = program.TensorBoard()
tb.configure(argv=[None, '--logdir', log_dir])
url = tb.launch()
print(f"🔗 TensorBoard is running at: {url}")
