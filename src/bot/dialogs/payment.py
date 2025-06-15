from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)

from src.config.env.env import get_env_var
from src.core.account.AccountManager import AccountManager, account_manager
from src.core.crypto.tron.TronClient import get_fee
from src.core.crypto.tron.TronManager import tron_manager
from src.core.currency.Amount import Amount, amount_from_trx
from src.core.exceptions.AccountNotFound import AccountNotFound
from src.util.logger import logger
from datetime import datetime

ADDRESS, AMOUNT, CONFIRMATION = range(3)

async def start_payment(update: Update, context: CallbackContext):
    user = update.effective_user
    if not user:
        logger.warning("Update without effective user")
        return ConversationHandler.END

    tg_id = user.id
    logger.debug(f"User {tg_id} started /transfer")

    reply_keyboard = [["Отмена"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👛 *Адрес получателя*:\n"
        "Введите адрес кошелька получателя (TRX).",
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return ADDRESS

async def receive_address(update: Update, context: CallbackContext):
    tg_id = update.effective_user.id
    address = update.message.text

    if address.lower() == "отмена":
        logger.info(f"User {tg_id} cancelled transfer")
        await update.message.reply_text(
            "❌ Перевод отменен. ",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if not tron_manager.client.validate_address(address):
        await update.message.reply_text(
            "🚫 *Неверный адрес* \n",
            parse_mode="Markdown",
        )
        return ADDRESS

    context.user_data["address"] = address

    await update.message.reply_text(
        "💸 *Сумма транзакции (TRX)*:\n",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True),
    )

    return AMOUNT

async def receive_amount(update: Update, context: CallbackContext):
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
        amount_trx = float(amount_input)
        if amount_trx <= 0:
            raise ValueError("Сумма должна быть положительной")

        amount = amount_from_trx(amount_trx)
        address = context.user_data["address"]
        context.user_data["amount_byn"] = amount.get_byn_amount()
        context.user_data["amount_trx"] = amount_trx

        fee = 0
        if not tron_manager.can_transfer_without_fees():
            fee = get_fee()

        await update.message.reply_text(
            "✅ *Подтвердите перевод*:\n\n"
            f"Получатель: `{address}`\n"
            f"Сумма: *{amount.get_byn_amount():.2f} BYN*\n"
            f"Комиссия: *{fee.get_byn_amount():.2f} BYN*\n\n"
            f"К оплате: *{(amount.get_byn_amount() + fee.get_byn_amount()):.2f} BYN*\n"
            f"Будет переведено: *{amount_input} TRX*\n",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["Отмена"], ["OK"]], resize_keyboard=True),
        )

        return CONFIRMATION

    except:
        await update.message.reply_text(
            "❌ *Перевод отменен*. Неверная сумма",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

async def confirm_transaction(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    tg_id = user.id
    confirmation = update.message.text.strip().lower()

    if confirmation == "отмена":
        logger.info(f"User {tg_id} cancelled payment")
        await update.message.reply_text(
            "Перевод отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    elif confirmation == "ok":
        address = context.user_data["address"]
        amount = context.user_data["amount_trx"]

        tron_manager.pay(address, amount_from_trx(amount))
        logger.info(f"Transaction confirmed: {amount:.2f} TRX to {address}")

        await update.message.reply_text(
            f"Перевод выполнен:\n"
            f"Сумма: {amount:.2f} TRX\n"
            f"Получатель: {address}",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Пожалуйста, нажмите *Отмена* или *OK*.",
            parse_mode="Markdown",
        )
        return CONFIRMATION

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


def get_payment_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("payment", start_payment)],
        states={
            ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address),
                CommandHandler("cancel", cancel),
            ],
            AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount),
                CommandHandler("cancel", cancel),
            ],
            CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_transaction),
                CommandHandler("cancel", cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )