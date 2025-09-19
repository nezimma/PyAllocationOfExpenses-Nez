from wordcloud import WordCloud
import matplotlib.pyplot as plt
import json
import numpy as np
from PIL import Image
from wordcloud.color_from_image import ImageColorGenerator

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

message = load_json('result.json')

texts = [msg['text'] for msg in message['messages'] if 'text' in msg]

def flatten_texts(texts):
    flattened = []
    for item in texts:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)
    return flattened

texts_flat = flatten_texts(texts)
full_text = ' '.join(str(t) for t in texts_flat)

# Массив русских стоп слов
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
    "конечно", "всю", "между", "это","ладно","просто", "ещё", "https", "", ""
}

# Разбить full_text на слова и удалить стоп-слова
filtered_words = [word for word in full_text.split() if word.lower() not in russian_stopwords]

filtered_text = ' '.join(filtered_words)

mask = np.array(Image.open('heard.png'))

wordcloud = WordCloud(
    scale=3,
    width=2000,
    height=1000,
    background_color='black',
    collocations=False,
    mask=mask,
    colormap='Set3'
).generate(filtered_text)

plt.figure(figsize=(20, 10))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis('off')
plt.show()
