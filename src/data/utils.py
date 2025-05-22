from decimal import Decimal, ROUND_UP

def round_byn(amount, base=5):
    """
    Округляет сумму в BYN вверх до двух знаков после запятой.

    Args:
        amount (float или Decimal): Сумма для округления.
        :param base:
        :param amount:

    Returns:
        Decimal: Округленная сумма.
    """
    return base * Decimal(amount / base).quantize(Decimal('0.1'), rounding=ROUND_UP)
