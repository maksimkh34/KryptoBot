from src.bot.bot_main import start_bot
from src.util.logger.instance import logger


def main():
    logger.info("main started")
    start_bot()

if __name__ == '__main__':
    main()
