from tronpy.keys import PrivateKey

from src.util.logger import logger

_STR_WAITING_FOR_PAYMENT = "WAITING_FOR_PAYMENT"
_STR_BLOCKED = "BLOCKED"
_STR_PRIVATE_KEY = "PRIVATE_KEY"

class TronWallet:
    def __init__(self, private_key: str, blocked = False, waiting_for_payment = False):
        self.waiting_for_payment = waiting_for_payment
        self.blocked = blocked
        self._private_key = private_key

    def get_private_key(self):
        return self._private_key

    def get_address(self):
        try:
            private_key = PrivateKey.fromhex(self._private_key)
            address = private_key.public_key.to_base58check_address()

            logger.debug(f"Converted private key to address: {address}")
            return address

        except Exception as e:
            logger.error(f"Failed to convert private key to address: {e}")
            raise ValueError(f"Некорректный приватный ключ: {e}")

    def to_dict(self):
        return {
            _STR_WAITING_FOR_PAYMENT: self.waiting_for_payment,
            _STR_BLOCKED: self.blocked,
            _STR_PRIVATE_KEY: self._private_key
        }

    @classmethod
    def from_dict(cls, data):
        return TronWallet(
            private_key=data[_STR_PRIVATE_KEY],
            blocked=data[_STR_BLOCKED],
            waiting_for_payment=data[_STR_WAITING_FOR_PAYMENT]
        )
