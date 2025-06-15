import src.config.files
from src.database.JsonFileStorage import JsonFileStorage

trx_config = JsonFileStorage(src.config.files.get_trx_config_filename(), default_value=[])
