import matplotlib.pyplot as plt
import shutil
import string
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import losses
import pandas as pd
import os

stop_list = [',','.','*','-','–','(',')','[',']','{','}','&','!','"',"'",'#','№',':',';','—','«','»','?','1','2','3','4','5','6','7','8','9','0','­']

def load_dataset():
    df = pd.read_csv('DatasetK.csv', sep='|')
    i = 1
    j = 1
    for index, row in df.iterrows():
        junk_text = str(row['data'])
        clear_text = junk_text
        for u in stop_list:
            clear_text = clear_text.replace(u,'')
        print(clear_text)
        if str(row['category']) == 'Ресторан и еда':
            with open(os.path.join('train_dir','Restaurans_food', f'a_text_{i}.txt'), 'w', encoding='utf-8') as f:
                f.write(clear_text)
            i+=1
        if str(row['category']) == 'Транспорт':
            with open(os.path.join('train_dir','Transport', f'b_text_{j}.txt'), 'w', encoding='utf-8') as f:
                f.write(clear_text)
            j+=1

load_dataset()

batch_size = 32
seed = 42

raw_train_ds = tf.keras.utils.text_dataset_from_directory( #тут назначаю 80% для обучения
    'train_dir',
    batch_size = batch_size,
    validation_split=0.2,
    subset='training',
    seed=seed
)

raw_val_ds = tf.keras.utils.text_dataset_from_directory( #тут 20% для тустеривония и проверки
    'train_dir',
    batch_size=batch_size,
    validation_split=0.2,
    subset='validation',
    seed=seed
)

raw_test_ds = tf.keras.utils.text_dataset_from_directory(
    'train_dir',
    batch_size=batch_size
)

max_features = 10000
sequence_length = 250
vectorize_layer = layers.TextVectorization(
    max_tokens=max_features,
    output_mode='int',
    output_sequence_length=sequence_length
)

train_text = raw_train_ds.map(lambda x, y:x)
vectorize_layer.adapt(train_text)

def vectorize_text(text, label):
    text = tf.expand_dims(text, -1)
    return vectorize_layer(text), label

text_bench, label_bench = next(iter(raw_test_ds))
first_review, first_label = text_bench[0], label_bench[0]
# print('Review ', first_review)
# print('Label ', first_label)
# print('Vectorize', vectorize_text(first_review, first_label))

train_ds = raw_train_ds.map(vectorize_text)
val_ds = raw_val_ds.map(vectorize_text)
test_ds = raw_test_ds.map(vectorize_text)

embedding_dim = 16

model = tf.keras.Sequential([
    layers.Embedding(max_features, embedding_dim),
    layers.Dropout(0.2),
    layers.GlobalAveragePooling1D(),
    layers.Dropout(0.2),
    layers.Dense(1, activation='sigmoid')
])

model.summary()

model.compile(loss=losses.BinaryCrossentropy(),
              optimizer='adam',
              metrics=[tf.metrics.BinaryAccuracy(threshold=0.5)])

epochs = 20
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=epochs
)

loss, accuracy = model.evaluate(test_ds)
print('loss: ', loss)
print('Accuracy: ', accuracy)

history_dict = history.history
history_dict.keys()

acc = history_dict['binary_accuracy']
val_acc = history_dict['val_binary_accuracy']
loss = history_dict['loss']
val_loss = history_dict['val_loss']

epochs = range(1, len(acc)+1)

plt.plot(epochs, loss, 'bo', label='Training loss')
plt.plot(epochs, val_loss, 'b', label='Validation loss')
plt.title('Training and validation loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()

plt.show()

plt.plot(epochs, acc, 'bo', label='Training acc')
plt.plot(epochs, val_acc, 'b', label='Validation acc')
plt.title('Training and validation accuracy')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.legend(loc='lower right')

plt.show()

export_model = tf.keras.Sequential([
    vectorize_layer,
    model
])

export_model.compile(
    loss=losses.BinaryCrossentropy(from_logits=False),
    optimizer='adam',
    metrics=['accuracy']
)

loss, accuracy = export_model.evaluate(raw_test_ds)
print(accuracy)


examples = [
    "Сегодня съездил на заправку и потратил 40 рублей",
    "Лимон  это цитрусовый фрукт принадлежащий к роду Citrus Он имеет желтую кожуру и кислый вкус что делает его популярным ингредиентом в кулинарии и напитках Лимон",
    "проспал учебу, пришлось вызвать такси за 15 рублей"
]

byte_examples = [s.encode('utf-8') for s in examples]

input_texts = tf.constant(byte_examples, dtype=tf.string)

predictions = export_model.predict(input_texts)
print(predictions)
vectorized_texts = vectorize_layer(input_texts)
predictions_m = model.predict(vectorized_texts)
print(predictions_m)



