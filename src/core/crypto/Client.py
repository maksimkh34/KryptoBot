from src.core.currency.Amount import Amount


class Client:
    def get_balance(self, addr):
        raise NotImplementedError

    def transfer(self, private_key: str, to_address: str, amount: Amount):
        raise NotImplementedError
