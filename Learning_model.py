import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import losses
from Data_base import db
import pandas as pd
import os
os.environ["PYTHONUTF8"] = "1"


MODEL_NAME = "expense_model"
MODEL_DIR = "models"
AUTOTUNE = tf.data.AUTOTUNE
models = None

os.makedirs(MODEL_DIR, exist_ok=True)

def main():
    db.init_model_table()

    choice = input("1 - Train new model\n2 - Use latest model\nChoose: ")

    if choice == "1":
        model = train_model()

        save_choice = input("Save this model? (y/n): ")
        if save_choice.lower() == "y":
            save_model(model)

    elif choice == "2":
        model = load_latest_model()
        if model is None:
            print("No saved models found.")
        else:
            print("Model loaded successfully.")

    else:
        print("Invalid choice.")


def train_model():

    stop_list = [',','.','*','-','–','(',')','[',']','{','}','&','!','"',"'",'#','№',':',';','—','«','»','?','­']
    #gg
    def load_dataset():
        df = pd.read_csv('DatasetK.csv', sep='|')
        i = 1
        j = 1
        for index, row in df.iterrows():
            clear_text = str(row['data'])
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

    # load_dataset()

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
        'test_dir',
        batch_size=batch_size
    )

    max_features = 20687
    sequence_length = 200
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

    train_ds = raw_train_ds.map(vectorize_text)
    val_ds = raw_val_ds.map(vectorize_text)
    test_ds = raw_test_ds.map(vectorize_text)


    train_ds = train_ds.cache().prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)
    test_ds = test_ds.cache().prefetch(buffer_size=AUTOTUNE)

    vocab_size = len(vectorize_layer.get_vocabulary())

    embedding_dim = 64
    model = tf.keras.Sequential([
        layers.Embedding(input_dim=vocab_size, output_dim=embedding_dim),
        layers.Conv1D(128, 5, activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.GlobalMaxPooling1D(),
        layers.Dropout(0.5),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(1, activation='sigmoid')
    ])


    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss=losses.BinaryCrossentropy(),
        metrics=[tf.keras.metrics.BinaryAccuracy(threshold=0.5),
                 tf.keras.metrics.Precision(),
                 tf.keras.metrics.Recall()])

    early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
                                                      patience=3, restore_best_weights=True)

    epochs = 30

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=[early_stopping]
    )

    loss, accuracy, precision, recall  = model.evaluate(test_ds)
    model.summary()
    print('loss: ', loss)
    print('Accuracy: ', accuracy)


    acc = history.history['binary_accuracy']
    val_acc = history.history['val_binary_accuracy']
    train_loss = history.history['loss']
    val_loss = history.history['val_loss']


    epochs_plt = range(1, len(acc)+1)

    plt.plot(epochs_plt, train_loss, 'bo', label='Training loss')
    plt.plot(epochs_plt, val_loss, 'b', label='Validation loss')
    plt.title('Training and validation loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()

    plt.show()

    plt.plot(epochs_plt, acc, 'bo', label='Training acc')
    plt.plot(epochs_plt, val_acc, 'b', label='Validation acc')
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
        "Сходил в ресторан, заказал суши ",
        "Зашел после учебы купить чебурек",
        "Сходил на неделю затариться продуктами",
        "Проспал учебу, пришлось вызвать такси за 15 рублей"
    ]

    def accuracy_text(text):
        input_texts = tf.constant([text])
        predictions = export_model.predict(input_texts)
        print(predictions)
        if predictions<=0.5:
            return 'Рестораны и еда'
        else:
            return 'Транспорт'

    byte_examples = [s.encode('utf-8') for s in examples]
    input_texts = tf.constant(byte_examples, dtype=tf.string)
    vectorized_texts = vectorize_layer(input_texts)
    predictions_m = model.predict(vectorized_texts)

    print(predictions_m)
    return export_model

def save_model(model):
    latest = db.get_latest_model(MODEL_NAME)

    if latest:
        _, last_version = latest
        new_version = last_version + 1
    else:
        new_version = 1

    file_path = os.path.join(
        MODEL_DIR,
        f"{MODEL_NAME}_v{new_version}.keras"
    )

    model.save(file_path)

    db.save_model_metadata(
        MODEL_NAME,
        file_path,
        new_version
    )

    print(f"Model saved as version {new_version}")


def load_latest_model():
    latest = db.get_latest_model(MODEL_NAME)

    if not latest:
        return None

    file_path, version = latest

    if not os.path.exists(file_path):
        print("Model file not found on disk.")
        return None

    print(f"Loading model version {version}")
    return tf.keras.models.load_model(file_path)








def init_model():
    global models

    latest = db.get_latest_model(MODEL_NAME)

    if not latest:
        print("No trained model found.")
        return None

    file_path, version = latest

    if not os.path.exists(file_path):
        print("Model file not found.")
        return None

    print(f"Loading model version {version}")
    model = tf.keras.models.load_model(file_path)
    return model


def predict_category(text: str):
    global models

    if models is None:
        raise ValueError("Model is not loaded.")

    input_text = tf.constant([text])
    prediction = models.predict(input_text, verbose=0)[0][0]

    if prediction <= 0.5:
        return 'Рестораны и еда'
    else:
        return 'Транспорт'


main()




