from telegram import Update
from telegram.ext import ContextTypes
from src.core.account.AccountManager import AccountManager, account_manager
from src.core.exceptions.AccountNotFound import AccountNotFound
from src.util.logger import logger
from functools import wraps

async def account_check(update: Update, context: ContextTypes) -> bool:
    if not update.effective_user:
        logger.warning("Update without effective user")
        return False

    tg_id = update.effective_user.id
    username = update.effective_user.username

    # Проверяем аккаунт
    account = account_manager.find_account(tg_id)

    if account is None:
        account_manager.add_account(tg_id)
        return True

    if account.is_blocked():
        logger.warning(f"Blocked account attempted access: {tg_id} (@{username})")
        await update.message.reply_text(
            "🚫 *Account blocked. @trxshv*",
            parse_mode="Markdown"
        )
        return False

    logger.debug(f"Account check passed for {tg_id} (@{username})")
    return True

def require_account(handler):
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes, *args, **kwargs):
        if await account_check(update, context):
            return await handler(update, context, *args, **kwargs)
        return None

    return wrapper