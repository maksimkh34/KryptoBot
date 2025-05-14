import uuid

from datetime import datetime
from typing import Dict, Any
from src.data import storage

def generate_order_id() -> str:
    """Генерирует уникальный ID заказа."""
    return str(uuid.uuid4())

def save_order(order_data: Dict[str, Any]) -> None:
    """Сохраняет данные заказа в orders.json."""
    orders = storage.load_file(storage.ORDERS)
    orders[order_data["order_id"]] = order_data
    storage.save_file(orders, storage.ORDERS)

def update_order_status(order_id: str, status: str, additional_data: Dict[str, Any] = None) -> None:
    """
    Обновляет статус заказа и добавляет дополнительные данные.

    Args:
        order_id: ID заказа.
        status: Новый статус.
        additional_data: Дополнительные данные для обновления.
    """
    orders = storage.load_file(storage.ORDERS)
    if order_id in orders:
        orders[order_id]["status"] = status
        orders[order_id]["updated_at"] = datetime.now().isoformat()
        if additional_data:
            orders[order_id].update(additional_data)
        storage.save_file(orders, storage.ORDERS)
