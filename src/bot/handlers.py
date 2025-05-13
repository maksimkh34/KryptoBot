from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from src.data.users import is_authorized
from src.config import load_config
from src.data.users import generate_auth_key
from src.data.storage import load_file, save_file, KEYS
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /start. Проверяет авторизацию пользователя.

    Args:
        update: Объект обновления от Telegram.
        context: Контекст обработчика.
    """
    user_id = str(update.effective_user.id)
    if is_authorized(user_id):
        await update.message.reply_text("Вы уже авторизованы!")
    else:
        await update.message.reply_text(
            "Добро пожаловать! Для использования бота необходимо авторизоваться.\n"
            "Введите /auth и ваш ключ доступа."
        )

async def generate_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /generate_key. Доступно только администратору.

    Args:
        update: Объект обновления от Telegram.
        context: Контекст обработчика.
    """
    config = load_config()
    user_id = update.effective_user.id
    if str(user_id) != config["ADMIN_ID"]:
        await update.message.reply_text("❌ Команда доступна только администратору!")
        return

    new_key = generate_auth_key()
    keys_data = load_file(KEYS)
    keys_data.setdefault("generated_keys", {})[new_key] = {"status": "active"}
    save_file(keys_data, KEYS)
    await update.message.reply_text(f"🔑 Новый ключ доступа:\n`{new_key}`", parse_mode="Markdown")

async def check_auth_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет, авторизован ли пользователь. Используется для команд, требующих авторизации.

    Args:
        update: Объект обновления от Telegram.
        context: Контекст обработчика.

    Returns:
        bool: True, если пользователь авторизован, иначе False.
    """
    user_id = str(update.effective_user.id)
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Для доступа к этой команде необходимо авторизоваться!")
        return False
    return True

def get_handlers() -> list[CommandHandler]:
    """
    Возвращает список обработчиков команд.

    Returns:
        list[CommandHandler]: Список обработчиков.
    """
    return [
        CommandHandler("start", start),
        CommandHandler("generate_key", generate_key),
    ]
