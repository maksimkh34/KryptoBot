from dotenv import load_dotenv
import os
from typing import Optional

from src.config.directories import get_root


def load_env() -> None:
    """Загружает .env файл из корневой директории проекта."""
    env_path = get_root() / ".env"
    load_dotenv(env_path)

def get_env_var(key: str, default: Optional[str] = None) -> str:
    """
    Возвращает значение переменной окружения по ключу.

    Args:
        key: Ключ переменной окружения.
        default: Значение по умолчанию, если ключ не найден.

    Returns:
        str: Значение переменной или default, если ключ не найден.
    """
    load_env()  # Загружаем .env при каждом вызове
    return os.getenv(key, default) or ""