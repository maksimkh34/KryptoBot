import os

from src.config import directories

_DATA_ACCOUNTS_FILENAME = "/accounts.json"

def wrap_filename(filename: str):
    if os.path.isfile(filename):
        return filename
    else:
        raise FileNotFoundError(f"File {filename} not found. Check paths")

def get_accounts_filename():
    return wrap_filename(directories.get_data() + _DATA_ACCOUNTS_FILENAME)

print(get_accounts_filename())
