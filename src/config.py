import os

from dotenv import load_dotenv
from typing import Optional

def load_config() -> dict:
    """
    Загружает конфигурацию из .env файла и возвращает словарь с проверенными значениями.

    Returns:
        dict: Словарь с конфигурационными параметрами.

    Raises:
        ValueError: Если обязательные переменные отсутствуют или некорректны.
    """
    load_dotenv()

    config = {
        "BOT_TOKEN": _get_env_var("BOT_TOKEN"),
        "TRON_NETWORK": _get_env_var("TRON_NETWORK", default="nile"),
        "ADMIN_ID": _get_env_var("ADMIN_ID"),
        "DRPC_API_KEY": _get_env_var("DRPC_API_KEY"),
        "TRONGRID_API_KEY": _get_env_var("TRONGRID_API_KEY", default=""),
    }

    # Валидация
    if not config["BOT_TOKEN"]:
        raise ValueError("BOT_TOKEN must be provided in .env")
    if config["TRON_NETWORK"] not in {"nile", "mainnet"}:
        raise ValueError("TRON_NETWORK must be 'nile' or 'mainnet'")
    if not config["ADMIN_ID"].isdigit():
        raise ValueError("ADMIN_ID must be a valid Telegram user ID")

    return config

def _get_env_var(name: str, default: Optional[str] = None) -> str:
    """Получает переменную окружения с указанным именем или возвращает default."""
    return os.getenv(name, default) or ""

def _get_float_env_var(name: str, default: float) -> float:
    """Получает переменную окружения как float или возвращает default."""
    try:
        return float(os.getenv(name, default))
    except (ValueError, TypeError):
        return default
