from decimal import Decimal, ROUND_HALF_UP

import src.util.configs

class Amount:
    def __init__(self, byn: Decimal | str | float = Decimal('0.0'), trx: Decimal | str | float = Decimal('0.0')):
        if byn and trx:
            raise ValueError("Нельзя одновременно указывать BYN и TRX")

        if trx:
            rate = Decimal(str(src.util.configs.trx_config.data['to_trx_rate']))
            self._byn = (Decimal(str(trx)) / rate)
        else:
            self._byn = Decimal(str(byn))

    def get_byn_amount(self) -> Decimal:
        return self._byn.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_to_trx(self) -> Decimal:
        rate = Decimal(str(src.util.configs.trx_config.data['to_trx_rate']))
        return self._byn * rate

    def __repr__(self):
        return f"{self.get_byn_amount()} BYN"

    def to_dict(self):
        return {
            "__type__": "Amount",
            "byn": str(self._byn) # Сохраняем как строку для точности
        }

    @classmethod
    def from_dict(cls, data: dict):
        if data.get("__type__") != "Amount":
            raise ValueError(f"Invalid type for Amount deserialization: {data.get('__type__')}")
        return cls(byn=data["byn"])

def amount_from_trx(trx_value: float | str) -> Amount:
    return Amount(trx=str(trx_value))
