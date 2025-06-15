import src.util.configs


class Amount:
    _BYN = 0

    def __init__(self, amount_byn: float = 0):
        self._BYN = amount_byn

    def get_byn_amount(self):
        return self._BYN

    def get_to_trx(self):
        return self._BYN * float(src.util.configs.trx_config.data['to_trx_rate'])

    def get_from_trx(self):
        return self._BYN * float(src.util.configs.trx_config.data['from_trx_rate'])

    def to_dict(self):
        return {
            "__type__": "Amount",
            "byn": self._BYN
        }

    @classmethod
    def from_dict(cls, data: dict):
        if data.get("__type__") != "Amount":
            raise ValueError(f"Invalid type for Amount deserialization: {data.get('__type__')}")
        return cls(amount_byn=data["byn"])

    def __repr__(self):
        return str(self.get_byn_amount())
