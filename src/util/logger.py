from datetime import datetime
from pathlib import Path
from inspect import currentframe, getframeinfo
from colorama import init, Fore, Style

import src.config.env.var_names
from src.config.directories import get_root
from src.config.env.env import get_env_var

init()

LEVELS = {
    "DBG": {"color": Fore.LIGHTBLACK_EX, "console_flag": "d"},
    "LOG": {"color": Fore.WHITE, "console_flag": "l"},
    "INF": {"color": Fore.CYAN, "console_flag": None},
    "WRN": {"color": Fore.YELLOW, "console_flag": None},
    "ERR": {"color": Fore.RED, "console_flag": None},
    "CRT": {"color": Fore.RED + Style.BRIGHT, "console_flag": None}
}


def _format_message(level: str, message: str, frame_info) -> str:
    timestamp = datetime.now()
    date = timestamp.strftime("%Y.%m.%d")
    time = timestamp.strftime("%H:%M:%S")
    module = Path(frame_info.filename).stem
    function = frame_info.function
    line = frame_info.lineno
    level_color = LEVELS[level]["color"]
    return (
        f"{Fore.BLUE}{date}{Style.RESET_ALL} "
        f"{Fore.CYAN}{time}{Style.RESET_ALL} "
        f"{level_color}[{level}]{Style.RESET_ALL} "
        f"{Fore.YELLOW}{{{module}.py}}{Style.RESET_ALL} "
        f"{Fore.GREEN}({function}){Style.RESET_ALL} "
        f"{Fore.MAGENTA}[ln #{line}]{Style.RESET_ALL}: "
        f"{level_color}{message}{Style.RESET_ALL}"
    )


def _format_file_message(level: str, message: str, frame_info) -> str:
    timestamp = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    module = Path(frame_info.filename).stem
    function = frame_info.function
    line = frame_info.lineno
    return f"{timestamp} [{level}] {{{module}.py}} ({function}) [ln #{line}]: {message}"


class Logger:
    def __init__(self, name: str):
        self.name = name
        self.log_level = get_env_var(src.config.env.var_names.LOG_LVL, default="cf").lower()
        self.log_path = None
        self._setup_file_handler()

    def _setup_file_handler(self):
        if "f" in self.log_level:
            timestamp = datetime.now().strftime("%Y.%m.%d.%H.%M.%S")
            log_file = f"{timestamp}.log"
            self.log_path = get_root() / "logs" / log_file
            self.log_path.parent.mkdir(exist_ok=True)

    def _should_log_to_console(self, level: str) -> bool:
        """Определяет, нужно ли выводить уровень в консоль."""
        if "c" not in self.log_level:
            return False
        if level in ("INF", "WRN", "ERR", "CRT"):
            return True
        flag = LEVELS[level]["console_flag"]
        return flag is not None and flag in self.log_level

    def _log(self, level: str, message: str):
        """Записывает лог."""
        if level not in LEVELS:
            return

        frame = currentframe().f_back.f_back
        frame_info = getframeinfo(frame)

        if self._should_log_to_console(level):
            print(_format_message(level, message, frame_info))

        if "f" in self.log_level and self.log_path:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(_format_file_message(level, message, frame_info) + "\n")
            except Exception as e:
                print(f"Failed to write to log file {self.log_path}: {str(e)}")

    def debug(self, message: str):
        self._log("DBG", message)

    def log(self, message: str):
        self._log("LOG", message)

    def info(self, message: str):
        self._log("INF", message)

    def warning(self, message: str):
        self._log("WRN", message)

    def error(self, message: str):
        self._log("ERR", message)

    def critical(self, message: str):
        self._log("CRT", message)

def get_logger(name: str = "main") -> Logger:
    return Logger(name)


logger = get_logger()
