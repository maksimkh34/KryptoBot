from telegram.ext import Application

from src.bot.dialogs.transfers import get_transfer_conversation
from src.bot.handlers import *
import src.config.env.env
import src.config.env.var_names
from src.util.logger import logger


def start_bot():
    token = src.config.env.env.get_env_var(src.config.env.var_names.BOT_TOKEN)
    if not token:
        logger.critical("BOT_TOKEN not found in .env")
        raise Exception(f"BOT_TOKEN is invalid: [{token}]")

    logger.debug("BOT_TOKEN loaded")

    app = Application.builder().token(token).build()

    app.add_handler(ch_start)
    app.add_handler(ch_get_account_balance)

    app.add_handler(get_transfer_conversation())


    logger.debug("polling...")
    app.run_polling()
