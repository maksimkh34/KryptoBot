import logging
from datetime import datetime
from logging import Formatter, StreamHandler, FileHandler
from pathlib import Path

from colorama import init, Fore, Style
from src.config.directories import get_root
from src.config.env import get_env_var

# Инициализация colorama для кроссплатформенного цветного вывода
init()


class ConsoleColorFormatter(Formatter):

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
    _logger = logging.getLogger("main")
    _logger.setLevel(logging.DEBUG)

    _logger.handlers.clear()

    log_level = get_env_var("LOGLVL", default="cf").lower()

    timestamp = datetime.now().strftime("%Y.%m.%d.%H.%M.%S")
    log_file = f"{timestamp}.log"
    log_path = get_root() / "logs" / log_file

    Path(log_path).resolve().parent.mkdir(exist_ok=True)

    if "c" in log_level:
        console_handler = StreamHandler()
        if "d" in log_level:
            console_level = logging.DEBUG
        elif "l" in log_level:
            console_level = logging.INFO
        else:
            console_level = logging.WARNING
        console_handler.setLevel(console_level)
        console_handler.setFormatter(ConsoleColorFormatter())
        _logger.addHandler(console_handler)

    if "f" in log_level:
        try:
            file_handler = FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(FileFormatter())
            _logger.addHandler(file_handler)
        except Exception as e:
            _logger.error(f"Failed to create FileHandler for {log_path}: {str(e)}")
            raise

    if not _logger.handlers:
        raise ValueError("No valid log handlers configured: 'LOGLVL' must contain 'c' and/or 'f'")

    return _logger
