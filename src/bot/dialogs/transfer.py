from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)

from src.bot.middleware import require_account
from src.config.env.env import get_env_var
from src.core.account.AccountManager import account_manager
from src.core.currency.Amount import Amount
from src.core.exceptions.AccountIsBlocked import AccountIsBlocked
from src.core.exceptions.AccountNotFound import AccountNotFound
from src.util.logger import logger
from datetime import datetime
import uuid

# Состояния диалога
RECIPIENT, AMOUNT = range(2)

@require_account
async def start_transfer(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    if not user:
        logger.warning("Update without effective user")
        return ConversationHandler.END

    tg_id = user.id
    logger.debug(f"User {tg_id} started /transfer")

    reply_keyboard = [["Отмена"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👤 Получатель перевода (ID):",
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return RECIPIENT

async def receive_recipient(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    tg_id = user.id
    recipient_input = update.message.text.strip()

    if recipient_input.lower() == "отмена":
        logger.info(f"User {tg_id} cancelled transfer")
        await update.message.reply_text(
            "❌ Перевод отменен. ",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    try:
        recipient_id = int(recipient_input)
        context.user_data["recipient_id"] = recipient_id
        logger.debug(f"Recipient {recipient_id} selected by {tg_id}")

        await update.message.reply_text(
            "💸 Введите сумму транзакции (BYN):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True),
        )
        return AMOUNT

    except AccountNotFound:
        logger.warning(f"Recipient {recipient_input} not found for {tg_id}")
        await update.message.reply_text("Пользователь не найден.",
            parse_mode="Markdown",
        )
        return RECIPIENT
    except ValueError as e:
        logger.warning(f"Invalid recipient input {recipient_input} by {tg_id}: {e}")
        await update.message.reply_text(
            "❌ Ошибка",
            parse_mode="Markdown"
        )
        return RECIPIENT

async def receive_amount(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    tg_id = user.id
    amount_input = update.message.text.strip()

    if amount_input.lower() == "отмена":
        logger.info(f"User {tg_id} cancelled transfer")
        await update.message.reply_text(
            "❌ *Перевод отменен*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    try:
        amount_byn = float(amount_input)
        if amount_byn <= 0:
            raise ValueError("Сумма должна быть положительной")

        amount = Amount(amount_byn)
        recipient_id = context.user_data["recipient_id"]

        if account_manager.transfer(tg_id, recipient_id, amount):
            new_balance = account_manager.get_byn_balance(tg_id)
            trx_amount = amount.get_to_trx()
            message = (
                f"✅ *Перевод выполнен* 🎉\n\n"
                f"Сумма: *{amount.get_byn_amount()} BYN* ({trx_amount:.2f} TRX)\n"
                f"Получатель: `{recipient_id}`\n"
                f"Ваш баланс: *{new_balance} BYN*\n\n"
            )
            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
            admin_id = get_env_var("ADMIN_ID")
            admin_message = (
                f"🔔 *Новый перевод 🔔*\n\n"
                f"Отправитель: `{tg_id}`\n"
                f"Получатель: `{recipient_id}`\n"
                f"Сумма: *{amount.get_byn_amount()} BYN* ({trx_amount:.2f} TRX)\n"
                f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n\n"
            )
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode="Markdown"
            )
            await context.bot.send_message(
                chat_id=recipient_id,
                text=f"🔔 Перевод от {tg_id}: *{amount.get_byn_amount()} BYN* ({amount.get_to_trx():.2f} TRX)",
                parse_mode="Markdown"
            )
            logger.info(f"Transfer {amount.get_byn_amount()} BYN from {tg_id} to {recipient_id} succeeded")
        else:
            await update.message.reply_text(
                "❌ *Ошибка перевода: недостаточно средств*",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
            logger.error(f"Transfer failed for {tg_id}: insufficient funds")
        return ConversationHandler.END
    except AccountIsBlocked:
        await update.message.reply_text(
            "❌ *Ошибка: аккаунт заблокирован*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.error(f"Access from blocked account: {tg_id}")
        return ConversationHandler.END
    except ValueError as e:
        logger.warning(f"Invalid amount input {amount_input} by {tg_id}: {e}")
        await update.message.reply_text(
            "❌ *Неверная сумма!* Введите число (например, 10)\n"
            "Или нажмите *Отмена*",
            parse_mode="Markdown",
        )
        return AMOUNT

async def cancel(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    tg_id = user.id
    username = user.username or f"User{tg_id}"
    logger.info(f"User {tg_id} (@{username}) cancelled transfer")
    await update.message.reply_text(
        "❌ *Перевод отменен*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

def generate_transaction_id():
    return str(uuid.uuid4())[:8]

def get_transfer_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("transfer", start_transfer)],
        states={
            RECIPIENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_recipient),
                CommandHandler("cancel", cancel),
            ],
            AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount),
                CommandHandler("cancel", cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )