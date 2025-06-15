from src.core.currency.Amount import Amount


_STR_TG_ID = "tg_id"
_STR_BLOCKED = "blocked"
_STR_BALANCE = "balance"

class Account:
    _tg_id = 1
    _blocked = False
    _balance = Amount(0)

    def __init__(self, tg_id: int,
                 is_blocked: bool = False,
                 init_balance: int = 0):
        self._tg_id = tg_id
        self._blocked = is_blocked
        self._balance = Amount(init_balance)

    def block(self):
        self._blocked = True

    def unblock(self):
        self._blocked = False

    def is_blocked(self):
        return self._blocked

    def get_balance(self):
        return self._balance.get_byn_amount()

    def get_balance_amount(self):
        return self._balance

    def get_id(self):
        return self._tg_id

    def to_dict(self):
        return {
            _STR_TG_ID: self._tg_id,
            _STR_BLOCKED: self._blocked,
            _STR_BALANCE: self._balance.to_dict()
        }

    def modify_balance(self, amount: float):
        self._balance = Amount(self._balance.get_byn_amount() + amount)

    @classmethod
    def from_dict(cls, data: dict):
        return Account(tg_id=data[_STR_TG_ID],
                       is_blocked=data[_STR_BLOCKED],
                       init_balance=data[_STR_BALANCE].get_byn_amount())

    def __repr__(self):
        return (f"Account [id {self._tg_id}] is [{"blocked" if self._blocked else "not blocked"}]. "
                f"Balance: {self._balance.get_byn_amount()}")
