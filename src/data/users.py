import secrets
import string
from .storage import load_json, save_json

def generate_auth_key() -> str:
    """
    Генерирует случайный ключ авторизации длиной 16 символов.

    Returns:
        str: Ключ авторизации.
    """
    chars = string.ascii_letters + string.digits + "@#$_&-+()/*:;!?"
    return "".join(secrets.choice(chars) for _ in range(16))

def add_user(user_id: str, auth_key: str) -> None:
    """
    Добавляет пользователя с ключом авторизации в users.json.

    Args:
        user_id: ID пользователя.
        auth_key: Ключ авторизации.
    """
    users = load_json("users.json")
    users[user_id] = {"auth_key": auth_key}
    save_json(users, "users.json")

def is_authorized(user_id: str) -> bool:
    """
    Проверяет, авторизован ли пользователь.

    Args:
        user_id: ID пользователя.

    Returns:
        bool: True, если пользователь авторизован, иначе False.
    """
    users = load_json("users.json")
    return user_id in users
