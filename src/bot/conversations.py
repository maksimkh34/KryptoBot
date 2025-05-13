import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from src.config import load_config
from src.data import storage
from src.data.orders import generate_order_id, save_order, update_order_status
from src.data.users import add_user
from src.crypto.factory import get_wallet_class
from src.bot.notifications import send_payment_receipt, send_payment_failure, send_insufficient_funds
from src.data.utils import round_byn
from tronpy.keys import PrivateKey

logger = logging.getLogger(__name__)

# Состояния для авторизации
AUTH_KEY = 0

# Состояния для платежа
CURRENCY, WALLET, AMOUNT, CONFIRMATION = range(1, 5)

async def auth_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс авторизации."""
    await update.message.reply_text("Введите ваш ключ авторизации:")
    return AUTH_KEY

async def process_auth_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенный ключ авторизации."""
    user_id = str(update.effective_user.id)
    input_key = update.message.text.strip()
    keys_data = storage.load_file(storage.KEYS)

    if input_key in keys_data.get("generated_keys", {}):
        if keys_data["generated_keys"][input_key]["status"] == "active":
            keys_data["generated_keys"][input_key]["status"] = "used"
            storage.save_file(keys_data, storage.KEYS)
            add_user(user_id, input_key)
            await update.message.reply_text("✅ Авторизация успешна!")
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ Ключ уже использован!")
    else:
        await update.message.reply_text("❌ Неверный ключ авторизации!")
    return ConversationHandler.END

async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс платежа."""
    from src.bot.handlers import check_auth_middleware
    if not await check_auth_middleware(update, context):
        return ConversationHandler.END

    order_id = generate_order_id()
    context.user_data["payment_data"] = {
        "order_id": order_id,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
        "created_at": datetime.now().isoformat(),
        "status": "created"
    }
    save_order(context.user_data["payment_data"])

    settings = storage.load_file(storage.SETTINGS)
    currencies = [[currency["code"] for currency in settings.get("currencies", [])]]
    if not currencies[0]:
        await update.message.reply_text("❌ Нет доступных валют!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    markup = ReplyKeyboardMarkup(
        currencies,
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Выберите валюту"
    )
    await update.message.reply_text("Выберите криптовалюту:", reply_markup=markup)
    return CURRENCY

async def process_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор валюты."""
    currency = update.message.text.strip().upper()
    settings = storage.load_file(storage.SETTINGS)
    valid_currencies = {c["code"] for c in settings.get("currencies", [])}

    if currency not in valid_currencies:
        await update.message.reply_text("❌ Валюта не поддерживается", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    context.user_data["payment_data"]["currency"] = currency
    update_order_status(
        context.user_data["payment_data"]["order_id"],
        "currency_selected",
        {"currency": currency}
    )
    await update.message.reply_text("Введите адрес кошелька получателя:", reply_markup=ReplyKeyboardRemove())
    return WALLET

async def process_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенный адрес кошелька."""
    wallet = update.message.text.strip()
    context.user_data["payment_data"]["wallet"] = wallet
    currency = context.user_data["payment_data"]["currency"]
    await update.message.reply_text(
        f"Введите сумму в {currency}:",
        reply_markup=ReplyKeyboardRemove()
    )
    update_order_status(
        context.user_data["payment_data"]["order_id"],
        "wallet_entered",
        {"to_address": wallet}
    )
    return AMOUNT

async def process_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенную сумму."""
    try:
        amount = float(update.message.text.replace(",", "."))
        context.user_data["payment_data"]["amount"] = amount
        config = load_config()
        settings = storage.load_file(storage.SETTINGS)

        # Найти валюту и её курс
        currency = context.user_data["payment_data"]["currency"]
        currency_info = next((c for c in settings.get("currencies", []) if c["code"] == currency), None)
        if not currency_info:
            await update.message.reply_text("❌ Ошибка конфигурации валюты!", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        rate_key = currency_info["rate_key"]
        rate = settings.get(rate_key, config.get("TRX_RATE", 3.25))
        byn_amount = round_byn(amount * rate)

        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        await update.message.reply_text(
            f"Сумма к оплате: {round_byn(byn_amount)} BYN\n"
            f"Курс: 1 {currency} = {rate} BYN\n\n"
            "Подтвердите платеж:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        update_order_status(
            context.user_data["payment_data"]["order_id"],
            "amount_entered",
            {"amount": amount, "byn_amount": float(byn_amount)}
        )
        return CONFIRMATION
    except ValueError:
        await update.message.reply_text("❌ Неверный формат суммы!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает подтверждение платежа."""
    query = update.callback_query
    await query.answer()
    payment_data = context.user_data.get("payment_data")
    if not payment_data:
        await query.edit_message_text("❌ Ошибка: данные платежа утеряны")
        return ConversationHandler.END

    order_id = payment_data.get("order_id", "UNKNOWN_ORDER")
    try:
        update_order_status(
            order_id=order_id,
            status="processing",
            additional_data={"updated_at": datetime.now().isoformat()}
        )
        settings = storage.load_file(storage.SETTINGS)
        currency = payment_data["currency"]
        currency_info = next((c for c in settings.get("currencies", []) if c["code"] == currency), None)
        if not currency_info:
            raise ValueError("Currency not found in settings")

        wallet_class = get_wallet_class(currency_info["wallet_class"])
        wallet = wallet_class()

        if not wallet.validate_address(payment_data["wallet"]):
            update_order_status(order_id, "failed", {"error": "Invalid address"})
            await query.edit_message_text("❌ Неверный адрес кошелька")
            return ConversationHandler.END

        wallets = storage.load_file(storage.WALLETS).get("active", [])
        selected_wallet = None
        for f_wallet in wallets:
            try:
                priv_key = PrivateKey(bytes.fromhex(f_wallet["private_key"]))
                address = priv_key.public_key.to_base58check_address()
                balance = wallet.get_balance(address)
                bandwidth = wallet.estimate_bandwidth_usage(address)
                if balance >= payment_data["amount"] and bandwidth > 0:
                    selected_wallet = {
                        "private_key": f_wallet["private_key"],
                        "address": address,
                        "balance": balance,
                        "bandwidth": bandwidth
                    }
                    break
            except Exception as e:
                logger.error(f"Ошибка проверки кошелька: {str(e)}")
                continue

        if not selected_wallet:
            update_order_status(order_id, "failed", {"error": "Insufficient funds"})
            await send_insufficient_funds(context.bot, payment_data, update.effective_user.username)
            await query.edit_message_text("⚠️ Операция будет выполнена вручную")
            return ConversationHandler.END

        txid = wallet.send_transaction(
            private_key=selected_wallet["private_key"],
            to_address=payment_data["wallet"],
            amount=payment_data["amount"]
        )
        update_order_status(
            order_id,
            "completed",
            {
                "txid": txid,
                "from_address": selected_wallet["address"],
                "final_amount": payment_data["amount"],
                "commission": 0,
                "updated_at": datetime.now().isoformat()
            }
        )
        await send_payment_receipt(
            context.bot,
            payment_data,
            txid,
            update.effective_user.username,
            selected_wallet["address"]
        )
        await query.edit_message_text(
            f"✅ Платеж успешно выполнен!\nTXID: `{txid}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Payment error: {str(e)}")
        update_order_status(
            order_id,
            "failed",
            {
                "error": str(e),
                "updated_at": datetime.now().isoformat()
            }
        )
        await send_payment_failure(
            context.bot,
            payment_data,
            str(e),
            update.effective_user.username
        )
        await query.edit_message_text("❌ Ошибка при выполнении платежа")
    finally:
        context.user_data.clear()
    return ConversationHandler.END

async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает отмену платежа."""
    query = update.callback_query
    await query.answer()
    order_id = context.user_data["payment_data"]["order_id"]
    update_order_status(order_id, "cancelled")
    await query.edit_message_text("❌ Платеж отменен")
    context.user_data.clear()
    return ConversationHandler.END

def get_auth_conversation() -> ConversationHandler:
    """Возвращает ConversationHandler для авторизации."""
    return ConversationHandler(
        entry_points=[CommandHandler("auth", auth_start)],
        states={
            AUTH_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_auth_key)]
        },
        fallbacks=[]
    )

def get_payment_conversation() -> ConversationHandler:
    """Возвращает ConversationHandler для платежей."""
    settings = storage.load_file(storage.SETTINGS)
    valid_currencies = "|".join(c["code"] for c in settings.get("currencies", []))
    return ConversationHandler(
        entry_points=[CommandHandler("pay", start_payment)],
        states={
            CURRENCY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.Regex(f"^{valid_currencies}$"),
                    process_currency
                )
            ],
            WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_wallet)
            ],
            AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_amount)
            ],
            CONFIRMATION: [
                CallbackQueryHandler(confirm_payment, pattern="^confirm$"),
                CallbackQueryHandler(cancel_payment, pattern="^cancel$")
            ]
        },
        fallbacks=[
            CommandHandler("start", cancel_payment),
            CommandHandler("pay", start_payment)
        ]
    )
