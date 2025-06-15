import json

from src.core.account.Account import Account
from src.core.currency.Amount import Amount
from src.util.logger.instance import logger


class AccountEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Account):
            acc = obj.to_dict()
            acc["__type__"] = "Account"
            return acc
        if isinstance(obj, Amount):
            return obj.to_dict()
        logger.error(f"Cannot serialize object of type {type(obj)}")
        return super().default(obj)


class AccountDecoder:
    @staticmethod
    def decode_hook(data: dict):
        if isinstance(data, dict):
            if data.get("__type__") == "Account":
                return Account.from_dict(data)
            if data.get("__type__") == "Amount":
                return Amount.from_dict(data)
        return data
