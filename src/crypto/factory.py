from typing import Type
from .wallet import CryptoWallet, TronWallet

def get_wallet_class(currency: str) -> Type[CryptoWallet]:
    """
    Возвращает класс кошелька для указанной валюты.

    Args:
        currency: Код валюты (например, 'TRX').

    Returns:
        Type[CryptoWallet]: Класс кошелька.

    Raises:
        ValueError: Если валюта не поддерживается.
    """
    wallets: dict[str, Type[CryptoWallet]] = {
        "TRX": TronWallet,
    }
    currency = currency.upper()
    if currency not in wallets:
        raise ValueError(f"Unsupported currency: {currency}")
    return wallets[currency]
