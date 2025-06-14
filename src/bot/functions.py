from src.util.instances import logger


async def start(update, context):
    logger.info(f"Пользователь {update.effective_user.id} отправил команду /start")
    await update.message.reply_text("Привет! Это бот для работы с TRX.")