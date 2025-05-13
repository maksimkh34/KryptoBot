import time
from tronpy.keys import PrivateKey
from src.crypto.wallet import TronWallet
from src.data.storage import load_json


def test_validate_address():
    """Проверяет валидацию адреса."""
    wallet = TronWallet()
    # Пример валидного адреса в Nile (замени на свой, если нужно)
    valid_address = "TCUFzxgsZ2pVbpELDhhyd7U9aP3yMthuy6"
    invalid_address = "invalid_address"

    print(f"Валидация адреса {valid_address}: {wallet.validate_address(valid_address)}")
    print(f"Валидация адреса {invalid_address}: {wallet.validate_address(invalid_address)}")


def test_get_balance():
    """Проверяет получение баланса для кошельков из wallets.json."""
    tron_wallet = TronWallet()
    wallets_data = load_json("wallets.json")
    if not wallets_data.get("active"):
        print("Ошибка: wallets.json пуст или не содержит поле 'active'")
        return

    for wallet in wallets_data["active"]:
        priv_key = wallet["private_key"]
        address = PrivateKey(bytes.fromhex(priv_key)).public_key.to_base58check_address()
        balance = tron_wallet.get_balance(address)
        print(f"Баланс кошелька {address}: {balance} TRX")


def test_send_transaction():
    """Проверяет перевод 1 TRX между двумя кошельками в обе стороны."""
    wallet = TronWallet()
    wallets_data = load_json("wallets.json")
    if len(wallets_data.get("active", [])) < 2:
        print("Ошибка: wallets.json должен содержать минимум 2 кошелька")
        return

    wallet1 = wallets_data["active"][0]
    wallet2 = wallets_data["active"][1]
    priv_key1 = wallet1["private_key"]
    priv_key2 = wallet2["private_key"]
    addr1 = PrivateKey(bytes.fromhex(priv_key1)).public_key.to_base58check_address()
    addr2 = PrivateKey(bytes.fromhex(priv_key2)).public_key.to_base58check_address()

    # Проверяем балансы
    initial_balance1 = wallet.get_balance(addr1)
    initial_balance2 = wallet.get_balance(addr2)
    print(f"Начальный баланс {addr1}: {initial_balance1} TRX")
    print(f"Начальный баланс {addr2}: {initial_balance2} TRX")

    if initial_balance1 < 1.0 or initial_balance2 < 1.0:
        print("Ошибка: Каждый кошелек должен иметь минимум 1 TRX")
        return

    # Перевод 1 TRX с wallet1 на wallet2
    print(f"Отправка 1 TRX с {addr1} на {addr2}...")
    try:
        txid1 = wallet.send_transaction(priv_key1, addr2, 1.0)
        print(f"Успех: TXID={txid1}")
        time.sleep(10)  # Ждем подтверждения
        balance1_after = wallet.get_balance(addr1)
        balance2_after = wallet.get_balance(addr2)
        print(f"Баланс {addr1} после: {balance1_after} TRX")
        print(f"Баланс {addr2} после: {balance2_after} TRX")
    except Exception as e:
        print(f"Ошибка при переводе с {addr1} на {addr2}: {str(e)}")

    # Перевод 1 TRX обратно с wallet2 на wallet1
    print(f"\nОтправка 1 TRX с {addr2} на {addr1}...")
    try:
        txid2 = wallet.send_transaction(priv_key2, addr1, 1.0)
        print(f"Успех: TXID={txid2}")
        time.sleep(10)  # Ждем подтверждения
        final_balance1 = wallet.get_balance(addr1)
        final_balance2 = wallet.get_balance(addr2)
        print(f"Финальный баланс {addr1}: {final_balance1} TRX")
        print(f"Финальный баланс {addr2}: {final_balance2} TRX")
    except Exception as e:
        print(f"Ошибка при переводе с {addr2} на {addr1}: {str(e)}")


def main():
    """Запускает все тесты."""
    print("=== Тестирование валидации адреса ===")
    test_validate_address()
    print("\n=== Тестирование получения баланса ===")
    test_get_balance()
    print("\n=== Тестирование отправки транзакций ===")
    test_send_transaction()


if __name__ == "__main__":
    main()
