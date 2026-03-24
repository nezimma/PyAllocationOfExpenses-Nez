# cloud/yandex_disk.py — загрузка файлов на Яндекс.Диск
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class YandexDiskClient:
    """Клиент для работы с Яндекс.Диском."""

    def __init__(self, token: str, base_url: str, backup_folder: str):
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"OAuth {token}",
        }
        self._base_url = base_url
        self._backup_folder = backup_folder

    def _create_folder(self, path: str):
        response = requests.put(f"{self._base_url}?path={path}", headers=self._headers)
        if response.status_code in (201, 409):
            logger.info(f"Folder ready: {path}")
        else:
            logger.error(f"Failed to create folder {path}: {response.text}")
            response.raise_for_status()

    def _upload_file(self, local_path: str, remote_path: str, overwrite: bool = True):
        res = requests.get(
            f"{self._base_url}/upload?path={remote_path}&overwrite={str(overwrite).lower()}",
            headers=self._headers,
        ).json()

        upload_url = res.get("href")
        if not upload_url:
            raise RuntimeError(f"Could not get upload URL: {res}")

        with open(local_path, "rb") as f:
            response = requests.put(upload_url, data=f)

        if response.status_code == 201:
            logger.info(f"File uploaded: {remote_path}")
        else:
            logger.error(f"Upload failed for {remote_path}: {response.text}")
            response.raise_for_status()

    def backup(self, local_file_path: str, tg_username: str | int) -> str:
        """Бекапит файл на Яндекс.Диск и возвращает путь загруженного файла."""
        date_folder = datetime.now().strftime("%Y.%m.%d")
        folder_path = f"{self._backup_folder}/{date_folder}"
        self._create_folder(folder_path)

        time_str = datetime.now().strftime("%H%M%S")
        remote_filename = f"audiofile_{tg_username}_{time_str}.ogg"
        remote_path = f"{folder_path}/{remote_filename}"

        self._upload_file(local_file_path, remote_path, overwrite=True)
        return remote_path
