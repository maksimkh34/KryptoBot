from telegram import Bot
from src.config import load_config
from src.data.storage import load_file, WALLETS, SETTINGS
from typing import Optional
from tronpy.keys import PrivateKey

async def send_payment_receipt(bot: Bot, payment_data: dict, txid: str, username: str, from_address: str) -> None:
    """
    Отправляет уведомление администратору о новом платеже.

    Args:
        bot: Экземпляр Telegram Bot.
        payment_data: Данные платежа (currency, wallet, amount).
        txid: ID транзакции.
        username: Имя пользователя Telegram.
        from_address: Адрес отправителя.
    """
    config = load_config()
    admin_id = config["ADMIN_ID"]
    settings = load_file(SETTINGS)
    byn_amount = round(payment_data["amount"] * settings.get("trx_rate", config["TRX_RATE"]), 2)

    message = (
        f"🆕 Новый платеж ({payment_data['currency']}):\n"
        f"👤 Пользователь: @{username}\n"
        f"📤 С кошелька: {from_address}\n"
        f"📥 На кошелек: {payment_data['wallet']}\n"
        f"💰 Сумма TRX: {payment_data['amount']}\n"
        f"💸 Сумма BYN: {byn_amount}\n"
        f"🔗 TXID: {txid}"
    )
    await bot.send_message(chat_id=admin_id, text=message)

async def send_payment_failure(bot: Bot, payment_data: dict, error: str, username: str, from_address: Optional[str] = None) -> None:
    """
    Отправляет уведомление администратору об ошибке платежа.

    Args:
        bot: Экземпляр Telegram Bot.
        payment_data: Данные платежа.
        error: Описание ошибки.
        username: Имя пользователя Telegram.
        from_address: Адрес отправителя (опционально).
    """
    config = load_config()
    admin_id = config["ADMIN_ID"]
    settings = load_file(SETTINGS)
    byn_amount = round(payment_data["amount"] * settings.get("trx_rate", config["TRX_RATE"]), 2)

    message = (
        f"❌ Ошибка платежа!\n"
        f"👤 Пользователь: @{username}\n"
        f"📤 С кошелька: {from_address or 'не определен'}\n"
        f"📥 На кошелек: {payment_data['wallet']}\n"
        f"💰 Сумма TRX: {payment_data['amount']}\n"
        f"💸 Сумма BYN: {byn_amount}\n"
        f"🚫 Ошибка: {error}"
    )
    await bot.send_message(chat_id=admin_id, text=message)

async def send_insufficient_funds(bot: Bot, payment_data: dict, username: str) -> None:
    """
    Отправляет уведомление администратору о недостатке средств.

    Args:
        bot: Экземпляр Telegram Bot.
        payment_data: Данные платежа.
        username: Имя пользователя Telegram.
    """
    from src.crypto.wallet import TronWallet

    config = load_config()
    admin_id = config["ADMIN_ID"]
    settings = load_file(SETTINGS)
    byn_amount = round(payment_data["amount"] * settings.get("trx_rate", config["TRX_RATE"]), 2)

    tron = TronWallet()
    wallets = load_file(WALLETS).get("active", [])
    wallets_info = []
    for wallet in wallets:
        try:
            priv_key = wallet["private_key"]
            address = PrivateKey(bytes.fromhex(priv_key)).public_key.to_base58check_address()
            balance = tron.get_balance(address)
            bandwidth = tron.estimate_bandwidth_usage(address)
            wallets_info.append(f"▪ {address}: {balance:.2f} TRX | BW: {bandwidth}")
        except Exception:
            continue

    message = (
        f"⚠️ Недостаточно средств для автоматической оплаты!\n"
        f"👤 Пользователь: @{username}\n"
        f"📥 На кошелек: {payment_data['wallet']}\n"
        f"💰 Требуемая сумма TRX: {payment_data['amount']}\n"
        f"💸 Сумма BYN: {byn_amount}\n"
        "Балансы кошельков:\n" + "\n".join(wallets_info)
    )
    await bot.send_message(chat_id=admin_id, text=message)
