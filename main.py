from wordcloud import WordCloud
import matplotlib.pyplot as plt
import json
import numpy as np
from PIL import Image
from wordcloud.color_from_image import ImageColorGenerator
import os

# def load_json(filename):
#     with open(filename, 'r', encoding='utf-8') as file:
#         return json.load(file)
#
# message = load_json('result.json')
#
# texts = [msg['text'] for msg in message['messages'] if 'text' in msg]
#
# def flatten_texts(texts):
#     flattened = []
#     for item in texts:
#         if isinstance(item, list):
#             flattened.extend(item)
#         else:
#             flattened.append(item)
#     return flattened
#
# texts_flat = flatten_texts(texts)
# full_text = ' '.join(str(t) for t in texts_flat)
#
# # Массив русских стоп слов







#
# russian_stopwords = {
#     "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а",
#     "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же",
#     "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от",
#     "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже",
#     "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был", "него",
#     "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом",
#     "себя", "ничего", "ей", "может", "они", "тут", "где", "есть", "надо",
#     "ней", "для", "мы", "тебя", "их", "чем", "была", "сам", "чтоб", "без",
#     "будто", "чего", "раз", "тоже", "себе", "под", "будет", "ж", "тогда",
#     "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним",
#     "здесь", "этом", "один", "почти", "мой", "тем", "чтобы", "нее", "сейчас",
#     "были", "куда", "зачем", "всех", "никогда", "можно", "при", "наконец",
#     "два", "об", "другой", "хоть", "после", "над", "больше", "тот", "через",
#     "эти", "нас", "про", "всего", "них", "какая", "много", "разве", "три",
#     "эту", "моя", "впрочем", "хорошо", "свою", "этой", "перед", "иногда",
#     "лучше", "чуть", "том", "нельзя", "такой", "им", "более", "всегда",
#     "конечно", "всю", "между", "это","ладно","просто", "ещё", "https", "type","link",
#     "text","tgs","bold","document_id", "sticker","custom_emoji","animatedsticker","webm","mention","webp","video_files","href", "","", "█"
# }
# # # Разбить full_text на слова и удалить стоп-слова
#
# #
# #
# #
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
# import os
#
# def read_all_txt_files(directory):
#     all_text = ""
#     for filename in os.listdir(directory):
#         if filename.endswith(".txt"):
#             filepath = os.path.join(directory, filename)
#             with open(filepath, 'r', encoding='utf-8') as file:
#                 all_text += file.read() + "\n"
#     return all_text
#
# # Пример использования:
# directory_path = "train_dir/Restaurans_food"
# full_text = read_all_txt_files(directory_path).replace('\n', ' ')
#
# # filtered_words = [word for word in full_text.split() if not any(stop_word in word.lower() for stop_word in russian_stopwords)]
# filtered_words = [word for word in full_text.split() if word.lower() not in russian_stopwords]
# filtered_text = ' '.join(filtered_words)
# print(len(filtered_text))  # Вся текстовая информация из всех txt файлов
#
# wordcloud = WordCloud(
#     scale=3,
#     width=2000,
#     height=1000,
#     background_color='black',
#     collocations=False,
#     colormap='Set3'
# ).generate(filtered_text)
#
# plt.figure(figsize=(20, 10))
# plt.imshow(wordcloud, interpolation='bilinear')
# plt.axis('off')
# plt.show()


import tensorflow as tf
from tensorboard.plugins import projector
import os

log_dir = 'logs/test-projector'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Примерные данные
words = ['apple', 'banana', 'carrot']
vectors = tf.Variable([[1.0, 0.5], [0.9, 0.6], [0.2, 0.8]], name='embedding_weights')

# Сохраняем metadata
with open(os.path.join(log_dir, 'metadata.tsv'), 'w', encoding='utf-8') as f:
    for word in words:
        f.write(f"{word}\n")

# Сохраняем чекпоинт
checkpoint = tf.train.Checkpoint(embedding=vectors)
checkpoint.save(os.path.join(log_dir, 'embedding.ckpt'))

# Настройка TensorBoard
config = projector.ProjectorConfig()
embedding = config.embeddings.add()
embedding.tensor_name = vectors.name
embedding.metadata_path = 'metadata.tsv'
projector.visualize_embeddings(log_dir, config)


