from telegram.ext import CommandHandler
from src.bot.functions import *

ch_start = CommandHandler("start", start)
ch_block = CommandHandler("block", block)
ch_get_id = CommandHandler("get_id", get_id)
ch_unblock = CommandHandler("unblock", unblock)
ch_get_account_balance = CommandHandler("balance", get_account_balance)
ch_max_amount = CommandHandler("max_amount", get_max_payment_amount)
ch_wallets_info = CommandHandler("wallets_info", get_wallets_info)
