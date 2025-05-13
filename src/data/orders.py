from datetime import datetime
import random
from .storage import load_file, save_file, ORDERS

def generate_order_id() -> str:
    """
    Генерирует уникальный ID заказа в формате ORDER_YYYYMMDD_XXXXXX.

    Returns:
        str: ID заказа (например, 'ORDER_20250513_123456').
    """
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = str(random.randint(100000, 999999))
    return f"ORDER_{date_part}_{random_part}"

def save_order(order_data: dict) -> None:
    """
    Сохраняет заказ в orders.json.

    Args:
        order_data: Данные заказа с полем 'order_id'.

    Raises:
        KeyError: Если в order_data отсутствует 'order_id'.
    """
    if "order_id" not in order_data:
        raise KeyError("order_data must contain 'order_id'")
    orders = load_file(ORDERS)
    orders[order_data["order_id"]] = order_data
    save_file(orders, ORDERS)

def update_order_status(order_id: str, status: str, additional_data: dict | None = None) -> None:
    """
    Обновляет статус заказа и добавляет дополнительные данные.

    Args:
        order_id: ID заказа.
        status: Новый статус.
        additional_data: Дополнительные данные для обновления (опционально).

    Raises:
        KeyError: Если заказ не найден.
    """
    orders = load_file(ORDERS)
    if order_id not in orders:
        raise KeyError(f"Order {order_id} not found")
    orders[order_id]["status"] = status
    orders[order_id]["updated_at"] = datetime.now().isoformat()
    if additional_data:
        orders[order_id].update(additional_data)
    save_file(orders, ORDERS)
