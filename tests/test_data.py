import string

import pytest
from unittest.mock import patch
from datetime import datetime
from src.data.storage import load_json, save_json, ensure_data_dir
from src.data.orders import generate_order_id, save_order, update_order_status
from src.data.users import generate_auth_key, add_user, is_authorized

def test_storage(tmp_path):
    """Тестирует чтение и запись JSON-файлов."""
    # Переопределяем DATA_DIR для тестов
    from src.data import storage
    storage.DATA_DIR = str(tmp_path)

    # Тест создания директории
    ensure_data_dir()
    assert tmp_path.exists()

    # Тест записи и чтения
    data = {"test": "value"}
    save_json(data, "test.json")
    assert load_json("test.json") == data

    # Тест чтения несуществующего файла
    assert load_json("nonexistent.json") == {}

def test_orders(tmp_path):
    """Тестирует управление заказами."""
    from src.data import storage
    storage.DATA_DIR = str(tmp_path)

    # Тест генерации order_id
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 5, 13)
        order_id = generate_order_id()
        assert order_id.startswith("ORDER_20250513_")
        assert len(order_id.split("_")[-1]) == 6

    # Тест сохранения заказа
    order_data = {"order_id": "ORDER_20250513_123456", "status": "created"}
    save_order(order_data)
    assert load_json("orders.json")["ORDER_20250513_123456"] == order_data

    # Тест обновления статуса
    update_order_status("ORDER_20250513_123456", "processing", {"amount": 100})
    updated = load_json("orders.json")["ORDER_20250513_123456"]
    assert updated["status"] == "processing"
    assert updated["amount"] == 100
    assert "updated_at" in updated

    # Тест ошибки для несуществующего заказа
    with pytest.raises(KeyError):
        update_order_status("INVALID", "failed")

def test_users(tmp_path):
    """Тестирует управление пользователями и ключами."""
    from src.data import storage
    storage.DATA_DIR = str(tmp_path)

    # Тест генерации ключа
    key = generate_auth_key()
    assert len(key) == 16
    assert all(c in (string.ascii_letters + string.digits + "@#$_&-+()/*:;!?") for c in key)

    # Тест добавления пользователя
    add_user("12345", "test_key")
    assert load_json("users.json")["12345"] == {"auth_key": "test_key"}

    # Тест проверки авторизации
    assert is_authorized("12345")
    assert not is_authorized("67890")
