from src.crypto.wallet import TronWallet

def get_wallet_class(wallet_class_name: str):
    """
    Возвращает класс кошелька по имени.

    Args:
        wallet_class_name: Название класса кошелька (например, 'TronWallet').

    Returns:
        type: Класс кошелька.

    Raises:
        ValueError: Если класс кошелька не найден.
    """
    wallet_classes = {
        "TronWallet": TronWallet
        # Добавьте другие классы кошельков здесь, например:
        # "EthWallet": EthWallet
    }
    wallet_class = wallet_classes.get(wallet_class_name)
    if not wallet_class:
        raise ValueError(f"Wallet class {wallet_class_name} not found")
    return wallet_class