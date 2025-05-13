from telegram import Bot
from src.config import load_config
from src.data import storage
from src.data.utils import round_byn
from typing import Optional
from tronpy.keys import PrivateKey
from datetime import datetime

async def send_payment_receipt(
    bot: Bot,
    payment_data: dict,
    txid: str,
    username: str,
    from_address: str,
    commission: float,
    total_amount: float
) -> None:
    """
    Отправляет уведомление администратору о новом платеже.

    Args:
        bot: Экземпляр Telegram Bot.
        payment_data: Данные платежа (currency, wallet, amount).
        txid: ID транзакции.
        username: Имя пользователя Telegram.
        from_address: Адрес отправителя.
        commission: Комиссия за транзакцию.
        total_amount: Итоговая сумма (amount + commission).
    """
    config = load_config()
    admin_id = config["ADMIN_ID"]
    settings = storage.load_file(storage.SETTINGS)
    currency = payment_data["currency"]
    currency_info = next((c for c in settings.get("currencies", []) if c["code"] == currency), None)
    currency_name = currency_info["name"] if currency_info else currency
    rate_key = currency_info["rate_key"] if currency_info else "trx_rate"
    byn_amount = round_byn(payment_data["amount"] * settings.get(rate_key, config["TRX_RATE"]))

    commission_note = f"\nВключена комиссия: {commission} {currency_name}" if commission > 0 else ""
    message = (
        f"🆕 Новый платеж ({currency_name}):\n"
        f"👤 Пользователь: @{username}\n"
        f"📤 С кошелька: `{from_address}`\n"
        f"📥 На кошелек: `{payment_data['wallet']}`\n"
        f"💰 Сумма: {payment_data['amount']} {currency_name}\n"
        f"💸 Комиссия: {commission} {currency_name}\n"
        f"➡️ Итого: {total_amount} {currency_name}\n"
        f"💵 Сумма BYN: {byn_amount}\n"
        f"🔗 TXID: `{txid}`{commission_note}"
    )
    await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")

async def send_payment_failure(
    bot: Bot,
    payment_data: dict,
    error: str,
    username: str,
    from_address: Optional[str] = None,
    commission: float = 0,
    total_amount: float = 0
) -> None:
    """
    Отправляет уведомление администратору об ошибке платежа.

    Args:
        bot: Экземпляр Telegram Bot.
        payment_data: Данные платежа.
        error: Описание ошибки.
        username: Имя пользователя Telegram.
        from_address: Адрес отправителя (опционально).
        commission: Комиссия за транзакцию.
        total_amount: Итоговая сумма (amount + commission).
    """
    config = load_config()
    admin_id = config["ADMIN_ID"]
    settings = storage.load_file(storage.SETTINGS)
    currency = payment_data["currency"]
    currency_info = next((c for c in settings.get("currencies", []) if c["code"] == currency), None)
    currency_name = currency_info["name"] if currency_info else currency
    rate_key = currency_info["rate_key"] if currency_info else "trx_rate"
    byn_amount = round_byn(payment_data["amount"] * settings.get(rate_key, config["TRX_RATE"]))

    commission_note = f"\nВключена комиссия: {commission} {currency_name}" if commission > 0 else ""
    message = (
        f"❌ Ошибка платежа!\n"
        f"👤 Пользователь: @{username}\n"
        f"📤 С кошелька: `{from_address or 'не определен'}`\n"
        f"📥 На кошелек: `{payment_data['wallet']}`\n"
        f"💰 Сумма: {payment_data['amount']} {currency_name}\n"
        f"💸 Комиссия: {commission} {currency_name}\n"
        f"➡️ Итого: {total_amount} {currency_name}\n"
        f"💵 Сумма BYN: {byn_amount}\n"
        f"🚫 Ошибка: {error}{commission_note}"
    )
    await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")

async def send_insufficient_funds(bot: Bot, payment_data: dict, username: str) -> None:
    """
    Отправляет уведомление администратору о недостатке средств.

    Args:
        bot: Экземпляр Telegram Bot.
        payment_data: Данные платежа.
        username: Имя пользователя Telegram.
    """
    from src.crypto.factory import get_wallet_class

    config = load_config()
    admin_id = config["ADMIN_ID"]
    settings = storage.load_file(storage.SETTINGS)
    currency = payment_data["currency"]
    currency_info = next((c for c in settings.get("currencies", []) if c["code"] == currency), None)
    currency_name = currency_info["name"] if currency_info else currency
    rate_key = currency_info["rate_key"] if currency_info else "trx_rate"
    byn_amount = round_byn(payment_data["amount"] * settings.get(rate_key, config["TRX_RATE"]))

    wallet_class = get_wallet_class(currency_info["wallet_class"] if currency_info else "TronWallet")
    wallet = wallet_class()
    wallets = storage.load_file(storage.WALLETS).get("active", [])
    wallets_info = []
    for w in wallets:
        try:
            priv_key = w["private_key"]
            address = PrivateKey(bytes.fromhex(priv_key)).public_key.to_base58check_address()
            balance = wallet.get_balance(address)
            bandwidth = wallet.estimate_bandwidth_usage(address)
            wallets_info.append(f"▪ `{address}`: {balance:.2f} {currency} | BW: {bandwidth}")
        except Exception:
            continue

    message = (
        f"⚠️ Недостаточно средств для автоматической оплаты!\n"
        f"👤 Пользователь: @{username}\n"
        f"💸 Валюта: @{currency_name}\n"
        f"📥 На кошелек: `{payment_data['wallet']}`\n"
        f"💰 Требуемая сумма {currency}: {payment_data['amount']}\n"
        f"💵 Сумма BYN: {byn_amount}\n"
        f"Балансы кошельков:\n" + "\n".join(wallets_info)
    )
    await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")

async def send_key_activation_notification(bot: Bot, username: str, user_id: str, key: str) -> None:
    """
    Отправляет уведомление администратору об активации нового ключа.

    Args:
        bot: Экземпляр Telegram Bot.
        username: Имя пользователя Telegram.
        user_id: ID пользователя.
        key: Активированный ключ.
    """
    config = load_config()
    admin_id = config["ADMIN_ID"]
    message = (
        f"🆕 Новый пользователь активировал ключ!\n"
        f"👤 Пользователь: @{username} (ID: {user_id})\n"
        f"🔑 Ключ: `{key}`\n"
        f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
