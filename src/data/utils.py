from decimal import Decimal, ROUND_UP

def round_byn(amount):
    """
    Округляет сумму в BYN вверх до двух знаков после запятой.

    Args:
        amount (float или Decimal): Сумма для округления.

    Returns:
        Decimal: Округленная сумма.
    """
    return Decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_UP)
