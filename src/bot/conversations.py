import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from src.config import load_config
from src.data.storage import load_json, save_json
from src.data.orders import generate_order_id, save_order, update_order_status
from src.data.users import add_user
from src.crypto.wallet import TronWallet
from src.crypto.factory import get_wallet_class
from src.bot.notifications import send_payment_receipt, send_payment_failure, send_insufficient_funds
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
    keys_data = load_json("../keys.json")

    if input_key in keys_data.get("generated_keys", {}):
        if keys_data["generated_keys"][input_key]["status"] == "active":
            keys_data["generated_keys"][input_key]["status"] = "used"
            save_json(keys_data, "../keys.json")
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

    currencies = [["TRX"]]
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
    if currency not in {"TRX"}:
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
        settings = load_json("../settings.json")
        byn_amount = round(amount * settings.get("trx_rate", config["TRX_RATE"]), 2)

        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        await update.message.reply_text(
            f"Сумма к оплате: {byn_amount} BYN\n"
            f"Курс: 1 TRX = {settings.get('trx_rate', config['TRX_RATE'])} BYN\n\n"
            "Подтвердите платеж:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        update_order_status(
            context.user_data["payment_data"]["order_id"],
            "amount_entered",
            {"amount": amount, "byn_amount": byn_amount}
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
        tron = TronWallet()
        if not tron.validate_address(payment_data["wallet"]):
            update_order_status(order_id, "failed", {"error": "Invalid address"})
            await query.edit_message_text("❌ Неверный адрес кошелька")
            return ConversationHandler.END

        wallets = load_json("../data/wallets.json").get("active", [])
        selected_wallet = None
        for wallet in wallets:
            try:
                priv_key = PrivateKey(bytes.fromhex(wallet["private_key"]))
                address = priv_key.public_key.to_base58check_address()
                balance = tron.get_balance(address)
                bandwidth = tron.estimate_bandwidth_usage(address)
                if balance >= payment_data["amount"] and bandwidth > 0:
                    selected_wallet = {
                        "private_key": wallet["private_key"],
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

        txid = tron.send_transaction(
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
        await query.edit_message_text("✅ Платеж успешно выполнен!")
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
    return ConversationHandler(
        entry_points=[CommandHandler("pay", start_payment)],
        states={
            CURRENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^TRX$'), process_currency)
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