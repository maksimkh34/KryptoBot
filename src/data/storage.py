import json
import os

# Константы для имен файлов
USERS = "users.json"
ORDERS = "orders.json"
KEYS = "keys.json"
WALLETS = "wallets.json"
SETTINGS = "settings.json"

# Путь к директории с данными
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

def load_file(filename):
    """Загружает данные из JSON-файла по имени."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_file(data, filename):
    """Сохраняет данные в JSON-файл по имени."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
