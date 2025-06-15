from src.util.logger import logger
from src.core.account.AccountManager import account_manager


async def start(update, context):
    logger.log(f"Пользователь {update.effective_user.id} отправил команду /start")
    await update.message.reply_text("Привет! Это бот для работы с TRX.")

async def get_account_balance(update, context):
    account_id = update.effective_user.id
    balance = account_manager.get_byn_balance(int(account_id))
    if balance == -1:
        await context.bot.send_message("")
    await context.bot.send_message()
