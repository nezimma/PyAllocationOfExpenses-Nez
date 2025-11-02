import requests
from datetime import datetime
# y0__xCTvNqABhiyqTsgm-aJ_hSew_w7aO1wuBwEl7e1vPjtdu_MpA

URL = 'https://cloud-api.yandex.net/v1/disk/resources'
TOKEN = 'y0__xCTvNqABhiyqTsgm-aJ_hSew_w7aO1wuBwEl7e1vPjtdu_MpA'
headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {TOKEN}'}

def create_folder(date):
    path = f'AllocationOfExpenses_voices/{date}'
    response = requests.put(f'{URL}?path={path}', headers=headers)
    if response.status_code in (201, 409):
        print(f"Папка '{path}' готова")
    else:
        print('Ошибка создания папки:', response.text)

def upload_file(loadfile, savefile, replace=False):
    res = requests.get(f'{URL}/upload?path={savefile}&overwrite={str(replace).lower()}', headers=headers).json()
    upload_url = res.get('href')
    if not upload_url:
        print("Не удалось получить ссылку для загрузки:", res)
        return
    with open(loadfile, 'rb') as f:
        response = requests.put(upload_url, data=f)
        if response.status_code == 201:
            print(f"Файл {savefile} загружен успешно")
        else:
            print(f"Ошибка загрузки файла {savefile}:", response.text)

def backup(local_file_path, tg_username):
    date_folder = datetime.now().strftime("%Y.%m.%d")

    # Проверяем и создаем папку с датой
    create_folder(date_folder)

    time_str = datetime.now().strftime("%H:%M:%S")
    remote_filename = f"audiofile_{tg_username}_{time_str}.ogg"
    remote_path = f"AllocationOfExpenses_voices/{date_folder}/{remote_filename}"

    upload_file(local_file_path, remote_path, replace=True)
    return remote_path





