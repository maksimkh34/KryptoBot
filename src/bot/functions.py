from src.bot.middleware import require_account, admin_command
from src.core.crypto.tron.TronManager import tron_manager
from src.util.logger import logger
from src.core.account.AccountManager import account_manager

async def start(update, context):
    logger.log(f"Пользователь {update.effective_user.id} отправил команду /start")
    await update.message.reply_text("Бот Додеп")

@require_account
async def get_account_balance(update, context):
    account_id = update.effective_user.id
    balance = account_manager.get_byn_balance(int(account_id))
    if balance == -1:
        await context.bot.send_message(text="🛡️ ADMIN", chat_id=update.effective_user.id)
        return
    await context.bot.send_message(text=f"💰 Баланс: {balance} BYN", chat_id=update.effective_user.id)

async def get_max_payment_amount(update, context):

    await context.bot.send_message(text=f"Максимальная сумма для оплаты: {tron_manager.get_max_payment_amount()}",
                                   chat_id=update.effective_user.id)

@admin_command
async def get_wallets_info(update, context):
    msg = ""
    for wallet in tron_manager.wallets:
        msg += (f"Wallet: {wallet.get_address()}\n"
                f"Balance: {tron_manager.client.get_balance(wallet.get_address())}\n"
                f"Bandwidth: {tron_manager.client.estimate_bandwidth_usage(wallet.get_address())}\n\n\n")

    await context.bot.send_message(text=msg, chat_id=update.effective_user.id)

@admin_command
async def block(update, context):
    tg_id = update.effective_message.text.replace('/block ', '')
    account_manager.block(int(tg_id))
    await context.bot.send_message(text=f"Пользователь заблокирован.",
                                   chat_id=update.effective_user.id)

@admin_command
async def unblock(update, context):
    tg_id = update.effective_message.text.replace('/unblock ', '')
    account_manager.unblock(int(tg_id))
    await context.bot.send_message(text=f"Пользователь разблокирован.",
                                   chat_id=update.effective_user.id)

async def get_id(update, context):
    await update.message.reply_text(
        f"ID: `{update.effective_user.id}`",
        parse_mode="Markdown",
    )