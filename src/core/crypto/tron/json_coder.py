import json
from src.core.crypto.tron.TronWallet import TronWallet
from src.util.logger import logger


class TronWalletEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TronWallet):
            wallet = obj.to_dict()
            wallet["__type__"] = "TronWallet"
            return wallet
        logger.error(f"Cannot serialize object of type {type(obj)}")
        return super().default(obj)


class TronWalletDecoder:
    @staticmethod
    def decode_hook(data: dict):
        if isinstance(data, dict):
            if data.get("__type__") == "TronWallet":
                return TronWallet.from_dict(data)
        return data