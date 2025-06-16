from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)
from decimal import Decimal, InvalidOperation

from src.bot.middleware import require_account
from src.config.env.env import get_env_var
from src.core.account.AccountManager import account_manager
from src.core.crypto.tron.TronClient import get_fee
from src.core.crypto.tron.TronManager import tron_manager, PayResult
from src.core.currency.Amount import Amount, amount_from_trx
from src.util.logger import logger
from datetime import datetime

ADDRESS, AMOUNT, CONFIRMATION = range(3)

@require_account
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
        logger.debug(f"User {tg_id} cancelled payment dialog at address step.")
        await update.message.reply_text("❌ Перевод отменен.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if not tron_manager.client.validate_address(address):
        await update.message.reply_text("🚫 *Неверный адрес*, попробуйте еще раз.", parse_mode="Markdown")
        return ADDRESS

    context.user_data["address"] = address
    await update.message.reply_text(
        "💸 *Сумма транзакции (TRX)*:\nВведите сумму в TRX для перевода.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True),
    )
    return AMOUNT


async def receive_amount(update: Update, context: CallbackContext):
    user = update.effective_user
    tg_id = user.id
    amount_input = update.message.text.strip()

    if amount_input.lower() == "отмена":
        logger.info(f"User {tg_id} cancelled payment dialog at amount step.")
        await update.message.reply_text("❌ *Перевод отменен*", parse_mode="Markdown",
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    try:
        amount_trx = Decimal(amount_input)
        if amount_trx <= 0:
            raise ValueError("Сумма должна быть положительной")

        amount = amount_from_trx(amount_trx)
        address = context.user_data["address"]

        try:
            _, fee_amount = tron_manager.choose_wallet(amount)
        except ValueError:
            msg = (
                f"❌ *Перевод отменен*. Недостаточно средств.\n"
                f"Нужно: {amount.format_trx()} TRX\n"
                f"Баланс: {tron_manager.get_max_payment_amount()} TRX"
            )
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
            admin_id = get_env_var("ADMIN_ID")
            await context.bot.send_message(
                chat_id=admin_id,
                text=msg,
                parse_mode="Markdown"
            )
            logger.error("Not enough balance: " + amount.format_trx())
            return ConversationHandler.END

        total_amount_to_pay = Amount(byn=(amount.get_byn_amount() + fee_amount.get_byn_amount()))

        context.user_data["payment_amount"] = amount
        context.user_data["total_amount_to_pay"] = total_amount_to_pay

        if not account_manager.can_pay(tg_id, total_amount_to_pay):
            await update.message.reply_text(
                f"❌ *Перевод отменен*. Недостаточно средств.\n"
                f"Нужно: {total_amount_to_pay.get_byn_amount():.2f} BYN\n"
                f"Баланс: {account_manager.get_byn_balance(tg_id):.2f} BYN",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "✅ *Подтвердите перевод*:\n\n"
            f"Получатель: `{address}`\n"
            f"Сумма: *{amount.get_byn_amount():.2f} BYN*\n"
            f"Комиссия: *{fee_amount.get_byn_amount():.2f} BYN*\n\n"
            f"Всего: *{total_amount_to_pay.get_byn_amount():.2f} BYN*\n"
            f"Будет переведено: *{amount_input} TRX*\n",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["Отмена"], ["OK"]], resize_keyboard=True),
        )
        return CONFIRMATION

    except (ValueError, InvalidOperation) as e:
        logger.warning(f"User {tg_id} entered invalid amount: {amount_input}. Error: {e}")
        await update.message.reply_text(
            "❌ *Неверная сумма*. Введите число, например: `12.5`",
            parse_mode="Markdown",
        )
        return AMOUNT

async def confirm_transaction(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    tg_id = user.id
    confirmation = update.message.text.strip().lower()

    if confirmation not in ["ok", "отмена"]:
        await update.message.reply_text("Пожалуйста, нажмите *Отмена* или *OK*.", parse_mode="Markdown")
        return CONFIRMATION

    if confirmation == "отмена":
        logger.info(f"User {tg_id} cancelled payment at confirmation step.")
        await update.message.reply_text("Перевод отменён.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    address = context.user_data["address"]
    payment_amount: Amount = context.user_data["payment_amount"]
    total_amount_to_pay: Amount = context.user_data["total_amount_to_pay"]

    if not account_manager.subtract_from_balance(tg_id, total_amount_to_pay):
        await update.message.reply_text(
            f"❌ *Перевод отменен*. Недостаточно средств.\n"
            f"Ваш баланс: {account_manager.get_byn_balance(tg_id):.2f} BYN",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    pay_result = tron_manager.pay(address, payment_amount)

    if pay_result == PayResult.NOT_ENOUGH_BALANCE:
        logger.critical(
            f"CRITICAL: Not enough funds on service wallets for payment! Amount: {payment_amount}. User: {tg_id}")
        account_manager.add_to_balance(tg_id, total_amount_to_pay)
        await update.message.reply_text(
            "❌ *Ошибка сервера*. На сервисных кошельках недостаточно средств. Повторите попытку позже. Средства возвращены на ваш баланс.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    logger.info(f"Transaction confirmed for user {tg_id}: {payment_amount.format_trx()} TRX to {address}")

    await update.message.reply_text(
        f"✅ *Перевод выполнен*\n\n"
        f"Сумма: {payment_amount.format_trx()} TRX\n"
        f"Получатель: {address}\n"
        f"Баланс: *{account_manager.get_byn_balance(tg_id):.2f} BYN*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    admin_id = get_env_var("ADMIN_ID")
    admin_message = (
        f"🔔 *Новый платеж 🔔*\n\n"
        f"Отправитель: `{tg_id}`\n"
        f"Получатель: `{address}`\n"
        f"Сумма: *{context.user_data['total_amount_to_pay']} BYN*\n"
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n\n"
    )
    sent_message = await context.bot.send_message(
        chat_id=admin_id,
        text=admin_message,
        parse_mode="Markdown"
    )
    await context.bot.pin_chat_message(chat_id=admin_id,
                                       message_id=sent_message.message_id, disable_notification=True)

    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info(f"User {user.id} cancelled the conversation.")
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def get_payment_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("payment", start_payment)],
        states={
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_transaction)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
