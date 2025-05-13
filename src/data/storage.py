import json
import os
import logging

# Константы для имен файлов
USERS = "users.json"
ORDERS = "orders.json"
KEYS = "keys.json"
WALLETS = "wallets.json"
SETTINGS = "settings.json"

# Путь к директории с данными
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

logger = logging.getLogger(__name__)

def load_file(filename):
    """Загружает данные из JSON-файла по имени."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        logger.warning(f"File {path} is missing or empty, returning empty dict")
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from {path}: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Error reading {path}: {str(e)}")
        return {}

def save_file(data, filename):
    """Сохраняет данные в JSON-файл по имени."""
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing to {path}: {str(e)}")
        raise
