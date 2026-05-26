# ml/file_model_repository.py
"""
Синхронный репозиторий метаданных модели на основе JSON-файла.
Используется в train.py — не требует БД и asyncpg.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

_META_FILENAME = "model_meta.json"


class FileModelRepository:
    """Хранит метаданные моделей в JSON-файле рядом с папкой models/."""

    def __init__(self, models_dir: str):
        self._path = os.path.join(models_dir, _META_FILENAME)
        self._data: dict = self._load()

    # ── internal ──────────────────────────────────────────────────

    def _load(self) -> dict:
        if os.path.exists(self._path):
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Не удалось прочитать {self._path}: {e}")
        return {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ── public API (синхронный, зеркалит ModelRepository) ─────────

    def get_latest(self, name: str) -> tuple | None:
        """Возвращает (file_path, version) или None."""
        entry = self._data.get(name)
        if not entry:
            return None
        return entry["file_path"], entry["version"]

    def save_metadata(self, name: str, file_path: str, version: int) -> None:
        self._data[name] = {"file_path": file_path, "version": version}
        self._save()
        logger.info(f"FileModelRepository: сохранено {name} v{version} → {file_path}")
