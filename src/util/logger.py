import logging
from datetime import datetime
from logging import Formatter, StreamHandler, FileHandler
from colorama import init, Fore, Style
from src.config.directories import get_root
from src.config.env import get_env_var

# Инициализация colorama для кроссплатформенного цветного вывода
init()


class ConsoleColorFormatter(Formatter):
    """Кастомный форматтер для консоли с цветами для разных блоков лога и уровня."""

    LEVEL_MAP = {
        logging.DEBUG: ("DBG", Fore.LIGHTBLACK_EX),
        logging.INFO: ("LOG", Fore.WHITE),
        logging.WARNING: ("WRN", Fore.YELLOW),
        logging.ERROR: ("ERR", Fore.RED),
        logging.CRITICAL: ("CRT", Fore.RED + Style.BRIGHT)
    }

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created)
        date = timestamp.strftime("%Y.%m.%d")
        time = timestamp.strftime("%H:%M:%S")
        level, level_color = self.LEVEL_MAP.get(record.levelno, ("UNK", Fore.WHITE))
        module = record.module
        function = record.funcName
        line = record.lineno
        message = record.getMessage()
        return (
            f"{Fore.BLUE}{date}{Style.RESET_ALL} "
            f"{Fore.CYAN}{time}{Style.RESET_ALL} "
            f"{level_color}[{level}]{Style.RESET_ALL} "
            f"{Fore.YELLOW}{{{module}.py}}{Style.RESET_ALL} "
            f"{Fore.GREEN}({function}){Style.RESET_ALL} "
            f"{Fore.MAGENTA}[ln #{line}]{Style.RESET_ALL}: "
            f"{level_color}{message}{Style.RESET_ALL}"
        )


class FileFormatter(Formatter):
    """Кастомный форматтер для файла без цветовых кодов."""

    LEVEL_MAP = {
        logging.DEBUG: "DBG",
        logging.INFO: "LOG",
        logging.WARNING: "WRN",
        logging.ERROR: "ERR",
        logging.CRITICAL: "CRT"
    }

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y.%m.%d %H:%M:%S")
        level = self.LEVEL_MAP.get(record.levelno, "UNK")
        module = record.module
        function = record.funcName
        line = record.lineno
        message = record.getMessage()
        return f"{timestamp} [{level}] {{{module}.py}} ({function}) [ln #{line}]: {message}"


def setup_logger() -> logging.Logger:
    """
    Настраивает и возвращает единый логгер для всей программы.

    Returns:
        Logger: Настроенный логгер.
    """
    # Получаем единый логгер с фиксированным именем
    logger = logging.getLogger("mybot")
    logger.setLevel(logging.DEBUG)

    # Удаляем существующие обработчики
    logger.handlers.clear()

    # Получаем уровень вывода логов из .env
    loglvl = get_env_var("LOGLVL", default="cf").lower()

    # Формируем имя файла логов: YYYY.MM.DD.HH.MM.SS.log
    timestamp = datetime.now().strftime("%Y.%m.%d.%H.%M.%S")
    log_file = f"logs/{timestamp}.log"
    log_path = get_root() / log_file

    # Создаем директорию для логов
    log_path.parent.mkdir(exist_ok=True)

    # Настройка обработчиков в зависимости от LOGLVL
    if "c" in loglvl:
        console_handler = StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ConsoleColorFormatter())
        logger.addHandler(console_handler)

    if "f" in loglvl:
        file_handler = FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FileFormatter())
        logger.addHandler(file_handler)

    if not logger.handlers:
        raise ValueError("No valid log handlers configured: 'LOGLVL' must contain 'c' and/or 'f'")

    return logger
