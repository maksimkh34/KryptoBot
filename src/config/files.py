import os

from src.config import directories

_DATA_ACCOUNTS_FILENAME = "/accounts.json"
_DATA_TRX_CONFIG_FILENAME = "/trx_config.json"
_DATA_TRX_WALLETS_FILENAME = "/trx_wallets.json"

def wrap_filename(filename: str):
    if not os.path.isfile(filename):
        open(filename, "w").close()
    return filename


def get_accounts_filename():
    return wrap_filename(directories.get_data() + _DATA_ACCOUNTS_FILENAME)

def get_trx_config_filename():
    return wrap_filename(directories.get_data() + _DATA_TRX_CONFIG_FILENAME)

def get_trx_wallets_filename():
    return wrap_filename(directories.get_data() + _DATA_TRX_WALLETS_FILENAME)
