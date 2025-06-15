from telegram.ext import CommandHandler
from src.bot.functions import *

ch_start = CommandHandler("start", start)
ch_get_account_balance = CommandHandler("balance", get_account_balance)
