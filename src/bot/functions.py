from src.util.instances.logger import logger


async def start(update, context):
    logger.log(f"Пользователь {update.effective_user.id} отправил команду /start")
    await update.message.reply_text("Привет! Это бот для работы с TRX.")
