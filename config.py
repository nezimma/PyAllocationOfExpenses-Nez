# config.py — централизованные настройки приложения
import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "12345")
    db_name: str = os.getenv("DB_NAME", "allocationofexpenses")
    port: int = int(os.getenv("DB_PORT", "5432"))


@dataclass
class BotConfig:
    token: str = os.getenv("BOT_TOKEN", "8231618759:AAFQiJ2pUf6ds8Gx4Ze41vVaiUjJoOAMTlU")


@dataclass
class CloudConfig:
    token: str = os.getenv("YANDEX_DISK_TOKEN", "y0__xCTvNqABhiyqTsgm-aJ_hSew_w7aO1wuBwEl7e1vPjtdu_MpA")
    base_url: str = "https://cloud-api.yandex.net/v1/disk/resources"
    backup_folder: str = "AllocationOfExpenses_voices"


@dataclass
class ModelConfig:
    name: str = "expense_model"
    dir: str = os.path.join(os.path.dirname(__file__), "models")
    max_features: int = 20687
    sequence_length: int = 200
    embedding_dim: int = 64
    batch_size: int = 32
    seed: int = 42
    epochs: int = 30
    train_dir: str = os.path.join(os.path.dirname(__file__), "train_dir")
    test_dir: str = os.path.join(os.path.dirname(__file__), "test_dir")


@dataclass
class AppConfig:
    database: DatabaseConfig = None
    bot: BotConfig = None
    cloud: CloudConfig = None
    model: ModelConfig = None

    def __post_init__(self):
        self.database = self.database or DatabaseConfig()
        self.bot = self.bot or BotConfig()
        self.cloud = self.cloud or CloudConfig()
        self.model = self.model or ModelConfig()


config = AppConfig()
