import json
import os
from typing import Any

DATA_DIR = "../data"

def ensure_data_dir() -> None:
    """Создает директорию data/, если она не существует."""
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filename: str) -> dict:
    """
    Читает JSON-файл из директории data/. Возвращает пустой словарь, если файл не существует.

    Args:
        filename: Имя файла (например, 'users.json').

    Returns:
        dict: Данные из файла или пустой словарь.
    """
    ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(data: Any, filename: str) -> None:
    """
    Сохраняет данные в JSON-файл в директории data/.

    Args:
        data: Данные для сохранения.
        filename: Имя файла (например, 'users.json').

    Raises:
        OSError: Если не удалось сохранить файл.
    """
    ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise OSError(f"Failed to save {filename}: {str(e)}")
