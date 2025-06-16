from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import src.util.configs

class Amount:
    def __init__(self, byn: Decimal | str | float = '0.0', trx: Decimal | str | float = '0.0'):
        byn_provided = byn != '0.0'
        trx_provided = trx != '0.0'

        if byn_provided and trx_provided:
            raise ValueError("Нельзя одновременно указывать BYN и TRX при создании Amount")

        self._byn: Decimal

        try:
            if trx_provided:
                rate = Decimal(str(src.util.configs.trx_config.data['to_trx_rate']))
                if rate == 0:
                    raise ValueError("Курс обмена TRX не может быть нулевым.")
                self._byn = Decimal(str(trx)) / rate
            else:
                self._byn = Decimal(str(byn))
        except (InvalidOperation, TypeError):
            raise ValueError("Некорректный формат суммы. Ожидалось число.")

    def format_trx(self) -> str:
        trx_value = self.get_to_trx()

        # Нормализуем Decimal для удаления экспоненциальной записи
        normalized = trx_value.normalize()

        # Преобразуем в строку и удаляем лишние нули
        s = str(normalized)

        # Если есть экспоненциальная запись (например, 1E+8), конвертируем в float и обратно
        if 'E' in s or 'e' in s:
            s = format(trx_value, 'f')

        # Удаляем лишние нули в конце
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s

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
            "byn": str(self._byn)
        }

    @classmethod
    def from_dict(cls, data: dict):
        if data.get("__type__") != "Amount":
            raise ValueError(f"Invalid type for Amount deserialization: {data.get('__type__')}")
        return cls(byn=data.get("byn", '0.0'))


def amount_from_trx(trx_value: float | str | Decimal) -> Amount:
    return Amount(trx=trx_value)