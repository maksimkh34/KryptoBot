from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from src.core.account.AccountManager import account_manager
from src.util.logger import logger
from functools import wraps
from src.core.is_admin import is_admin


async def middleware_is_admin(update: Update) -> bool:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "🚫 Not admin",
            parse_mode="Markdown"
        )
        logger.warning(f"{update.effective_user.id} //"
                       f" {update.effective_user.username} tried to use admin command {update.effective_message.text}")
        return False
    return True


async def account_check(update: Update) -> bool:
    if not update.effective_user:
        logger.warning("Update without effective user")
        return False

    tg_id = update.effective_user.id
    username = update.effective_user.username

    if is_admin(tg_id):
        return True

    account = account_manager.find_account(tg_id)

    if account is None:
        account = account_manager.add_account(tg_id)
        logger.info(f"New account created for {tg_id} and is now blocked.")

    if account.is_blocked():
        logger.warning(f"Blocked account attempted access: {tg_id} (@{username})")
        await update.message.reply_text(
            "🚫 *Аккаунт заблокирован.*\n\nОбратитесь к администратору для активации.",
            parse_mode="Markdown"
        )
        return False

    logger.debug(f"Account check passed for {tg_id} (@{username})")
    return True


def require_account(handler):
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes, *args, **kwargs):
        if not await account_check(update):
            return ConversationHandler.END
        return await handler(update, context, *args, **kwargs)
    return wrapper

def admin_command(handler):
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes, *args, **kwargs):
        if await middleware_is_admin(update):
            return await handler(update, context, *args, **kwargs)
        return None
    return wrapper