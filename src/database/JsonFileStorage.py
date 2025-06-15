import json
import os
from typing import Any

from src.util.logger import logger


class JsonFileStorage:
    def __init__(self, file_path: str, decode_hook = None, encoder = None, default_value: Any = None):
        """
        Creates JSON storage
        :param file_path: path to storage
        :param default_value: value that should be returned if storage is empty
        """
        self.file_path = file_path
        self.default_value = default_value
        self._decode_hook = decode_hook
        self._encoder = encoder
        self._data = self._load()

    def _load(self) -> Any:
        if not os.path.exists(self.file_path) or os.path.getsize(self.file_path) == 0:
            return self.default_value

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                if self._decode_hook is None:
                    data = json.load(f)
                else:
                    data = json.load(f, object_hook=self._decode_hook)
                logger.debug(f"Loaded data from {self.file_path}")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {self.file_path}: {str(e)}")
            return self.default_value
        except Exception as e:
            logger.error(f"Error reading {self.file_path}: {str(e)}")
            return self.default_value

    def _save(self) -> None:
        try:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                if self._encoder is None:
                    json.dump(self._data, f, indent=2)
                else:
                    json.dump(self._data, f, indent=2, cls=self._encoder)
            logger.debug(f"Saved data to {self.file_path}")
        except Exception as e:
            logger.error(f"Error writing to {self.file_path}: {str(e)}")
            raise

    def create(self):
        if not os.path.isfile(self.file_path):
            open(self.file_path, "w").close()

    @property
    def data(self) -> Any:
        return self._data

    @data.setter
    def data(self, value: Any) -> None:
        self._data = value
        self._save()
