# cloud/__init__.py
from config import config
from cloud.yandex_disk import YandexDiskClient

disk = YandexDiskClient(
    token=config.cloud.token,
    base_url=config.cloud.base_url,
    backup_folder=config.cloud.backup_folder,
)
