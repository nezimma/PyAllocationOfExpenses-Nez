# ТУТ НАХОДИТСЯ ПРЕОБРАХОВАНИЕ ТЕКСТА В ОБЛАКО СЛОВ ДЛЯ КРАСОТЫ

from wordcloud import WordCloud
import matplotlib.pyplot as plt
import json
import numpy as np
from PIL import Image
from wordcloud.color_from_image import ImageColorGenerator
import os


# # Массив русских стоп слов
#
russian_stopwords = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а",
    "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же",
    "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от",
    "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже",
    "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был", "него",
    "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом",
    "себя", "ничего", "ей", "может", "они", "тут", "где", "есть", "надо",
    "ней", "для", "мы", "тебя", "их", "чем", "была", "сам", "чтоб", "без",
    "будто", "чего", "раз", "тоже", "себе", "под", "будет", "ж", "тогда",
    "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним",
    "здесь", "этом", "один", "почти", "мой", "тем", "чтобы", "нее", "сейчас",
    "были", "куда", "зачем", "всех", "никогда", "можно", "при", "наконец",
    "два", "об", "другой", "хоть", "после", "над", "больше", "тот", "через",
    "эти", "нас", "про", "всего", "них", "какая", "много", "разве", "три",
    "эту", "моя", "впрочем", "хорошо", "свою", "этой", "перед", "иногда",
    "лучше", "чуть", "том", "нельзя", "такой", "им", "более", "всегда",
    "конечно", "всю", "между", "это","ладно","просто", "ещё", "https", "type","link",
    "text","tgs","bold","document_id", "sticker","custom_emoji","animatedsticker","webm","mention","webp","video_files","href", "","", "█"
}

#

# # mask = np.array(Image.open('heard.png'))
# #
# # wordcloud = WordCloud(
# #     scale=3,
# #     width=2000,
# #     height=1000,
# #     background_color='black',
# #     collocations=False,
# #     mask=mask,
# #     colormap='Set3'
# # ).generate(filtered_text)
# #
# # plt.figure(figsize=(20, 10))
# # plt.imshow(wordcloud, interpolation='bilinear')
# # plt.axis('off')
# # plt.show()
#
#

# def delete_stop_words(base_dir):
#     import os
#
#     # Путь к основной директории с папками и файлами
#     base_dir = base_dir
#
#     def remove_stop_words(text, stop_words):
#         words = text.split()
#         filtered_words = [word for word in words if word.lower() not in stop_words]
#         return ' '.join(filtered_words)
#
#     for root, dirs, files in os.walk(base_dir):
#         for filename in files:
#             file_path = os.path.join(root, filename)
#             with open(file_path, 'r', encoding='utf-8') as file:
#                 text = file.read()
#
#             cleaned_text = remove_stop_words(text, russian_stopwords)
#
#             with open(file_path, 'w', encoding='utf-8') as file:
#                 file.write(cleaned_text)
#
#     print("Обработка завершена.")
#
# if input("Введи y для очистки папок от стоп слов") == "y":
#     delete_stop_words(input("Введи директорию"))
#
#
# import os
# def word_cloude_tf(directory_path):
#     def read_all_txt_files(directory):
#         all_text = ""
#         for filename in os.listdir(directory):
#             if filename.endswith(".txt"):
#                 filepath = os.path.join(directory, filename)
#                 with open(filepath, 'r', encoding='utf-8') as file:
#                     all_text += file.read() + "\n"
#         return all_text
#
#     # Пример использования:
#     full_text = read_all_txt_files(directory_path).replace('\n', ' ')
#
#     russian_stopwords = []
#
#     # filtered_words = [word for word in full_text.split() if not any(stop_word in word.lower() for stop_word in russian_stopwords)]
#     filtered_words = [word for word in full_text.split() if word.lower() not in russian_stopwords]
#     filtered_text = ' '.join(filtered_words)
#     print(len(filtered_text))  # Вся текстовая информация из всех txt файлов
#
#     wordcloud = WordCloud(
#         scale=3,
#         width=2000,
#         height=1000,
#         background_color='black',
#         collocations=False,
#         colormap='Set3'
#     ).generate(filtered_text)
#
#     plt.figure(figsize=(20, 10))
#     plt.imshow(wordcloud, interpolation='bilinear')
#     plt.axis('off')
#     plt.show()
#
# if input('введи y для облака слов') == "y":
#     word_cloude_tf(input("Введи директорию в которой хочешь проверить облако"))




# import tensorflow as tf
# from tensorboard.plugins import projector
# import os
#
# log_dir = 'logs/test-projector'
# if not os.path.exists(log_dir):
#     os.makedirs(log_dir)
#
# # Примерные данные
# words = ['apple', 'banana', 'carrot']
# vectors = tf.Variable([[1.0, 0.5], [0.9, 0.6], [0.2, 0.8]], name='embedding_weights')
#
# # Сохраняем metadata
# with open(os.path.join(log_dir, 'metadata.tsv'), 'w', encoding='utf-8') as f:
#     for word in words:
#         f.write(f"{word}\n")
#
# # Сохраняем чекпоинт
# checkpoint = tf.train.Checkpoint(embedding=vectors)
# checkpoint.save(os.path.join(log_dir, 'embedding.ckpt'))
#
# # Настройка TensorBoard
# config = projector.ProjectorConfig()
# embedding = config.embeddings.add()
# embedding.tensor_name = vectors.name
# embedding.metadata_path = 'metadata.tsv'
# projector.visualize_embeddings(log_dir, config)


#
# from tensorboard.plugins import projector
# import io
# import os
# import tensorflow as tf
# import Learning_model
# import datetime
# import shutil
#
# # === 1. Настройка путей ===
# timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
#
# fit_log_dir = os.path.join("logs", "fit")
# os.makedirs(fit_log_dir, exist_ok=True)
#
# projector_log_dir = os.path.join("logs", "projector")
# os.makedirs(projector_log_dir, exist_ok=True)
#
# # === 2. TensorBoard callback ===
# tensorboard_callback = tf.keras.callbacks.TensorBoard(
#     log_dir=fit_log_dir,
#     histogram_freq=1,
#     write_graph=True,
#     write_images=True
# )
#
# # === 3. Обучение модели ===
# history = Learning_model.model.fit(
#     Learning_model.train_ds,
#     validation_data=Learning_model.val_ds,
#     epochs=Learning_model.epochs,
#     callbacks=[tensorboard_callback, Learning_model.early_stopping]
# )
#
# # === 4. Извлекаем веса и словарь ===
# embedding_layer = Learning_model.model.layers[0]
# embedding_weights = embedding_layer.get_weights()[0]
# vocab = Learning_model.vectorize_layer.get_vocabulary()
#
# # Приводим размеры к совпадению
# embedding_weights = embedding_weights[:len(vocab)-1, :]
#
# # === 5. Сохраняем веса для Projector ===
# embedding_var = tf.Variable(embedding_weights)
# checkpoint = tf.train.Checkpoint(embedding=embedding_var)
# checkpoint.save(os.path.join(projector_log_dir, "embedding.ckpt"))
#
# # === 6. Сохраняем метаданные ===
# metadata_file = os.path.join(projector_log_dir, "metadata.tsv")
# with io.open(metadata_file, "w", encoding="utf-8") as f:
#     for word in vocab:
#         f.write(f"{word}\n")
#
# # === 7. Конфигурация для Projector ===
# config = projector.ProjectorConfig()
# embedding = config.embeddings.add()
# embedding.tensor_name = "word_embedding:0"  # имя переменной без ":0"
# embedding.metadata_path = "metadata.tsv"
# projector.visualize_embeddings(projector_log_dir, config)
#
# # === 8. Проверка ===
# print("Embedding shape:", embedding_weights.shape)
# print("Vocab length:", len(vocab))
# print(f"Logs saved to: {projector_log_dir}")
# print(f"TensorBoard fit logs: {fit_log_dir}")

text_date = {"date": "неделя"}

interval = {"неделя":7,
            "день":1}

print(interval[text_date['date']])
