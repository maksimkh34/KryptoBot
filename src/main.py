import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from src.config import load_config
from src.bot.handlers import get_handlers
from src.bot.conversations import (get_auth_conversation, get_payment_conversation, add_wallet,
                                   remove_wallet, wallets_info, balance)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def text_fallback(update, context) -> None:
    """Обрабатывает текстовые сообщения, требующие авторизации."""
    from src.bot.handlers import check_auth_middleware
    await check_auth_middleware(update, context)

def main() -> None:
    """Запускает Telegram-бота."""
    config = load_config()
    application = Application.builder().token(config["BOT_TOKEN"]).build()

    # Регистрация обработчиков команд
    for handler in get_handlers():
        application.add_handler(handler)

    # Регистрация диалогов
    application.add_handler(get_auth_conversation())
    application.add_handler(get_payment_conversation())

    # Fallback для текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_fallback))

    application.add_handler(CommandHandler("add_wallet", add_wallet))
    application.add_handler(CommandHandler("remove_wallet", remove_wallet))
    application.add_handler(CommandHandler("wallets_info", wallets_info))
    application.add_handler(CommandHandler("balance", balance))

    application.run_polling()

if __name__ == "__main__":
    main()
