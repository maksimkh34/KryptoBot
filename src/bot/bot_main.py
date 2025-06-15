from telegram.ext import Application
from src.bot.handlers import *
import src.config.env.env
import src.config.env.var_names


def start_bot():
    token = src.config.env.env.get_env_var(src.config.env.var_names.BOT_TOKEN)
    if not token:
        logger.critical("BOT_TOKEN not found in .env")
        raise Exception(f"BOT_TOKEN is invalid: [{token}]")

    logger.debug("BOT_TOKEN loaded")

    app = Application.builder().token(token).build()
    app.add_handler(ch_start)

    logger.debug("polling...")
    app.run_polling()
