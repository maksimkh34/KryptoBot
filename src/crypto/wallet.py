import requests

from abc import ABC, abstractmethod
from decimal import Decimal
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from src.config import load_config
from src.data.logger import logger


class CryptoWallet(ABC):
    """Абстрактный базовый класс для криптовалютных кошельков."""

    @abstractmethod
    def validate_address(self, address: str) -> bool:
        """Проверяет валидность адреса кошелька."""
        pass

    @abstractmethod
    def get_balance(self, address: str) -> float:
        """Получает баланс кошелька в нативной валюте."""
        pass

    @abstractmethod
    def send_transaction(self, private_key: str, to_address: str, amount: float) -> str:
        """Отправляет транзакцию и возвращает TXID."""
        pass

class TronWallet(CryptoWallet):
    """Реализация кошелька для сети Tron."""

    def __init__(self):
        config = load_config()
        self.network = config["TRON_NETWORK"]
        self.api_key = config.get("TRONGRID_API_KEY", "")
        self.client = self._get_client()

    def _get_client(self) -> Tron:
        """Создает клиента Tron в зависимости от сети."""
        if self.network == "mainnet":
            if not self.api_key:
                raise ValueError("TRONGRID_API_KEY is required for mainnet (TronGrid)")
            provider_url = "https://api.trongrid.io"
        elif self.network == "nile":
            provider_url = "https://nile.trongrid.io"
        else:
            raise ValueError(f"Unsupported network: {self.network}")

        try:
            provider = HTTPProvider(provider_url, api_key=self.api_key if self.network == "mainnet" else None)
            client = Tron(provider=provider)
            # Проверка подключения
            client.get_block(0)  # Запрашиваем генезис-блок
            logger.info(f"Connected to Tron network: {self.network}")
            return client
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ошибка подключения к сети Tron ({self.network}): {str(e)}")
            raise RuntimeError(
                f"Failed to connect to Tron network: {str(e)}. Check TRONGRID_API_KEY for mainnet or network availability for nile")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при подключении к Tron ({self.network}): {str(e)}")
            raise RuntimeError(f"Unexpected error connecting to Tron network: {str(e)}")

    def validate_address(self, address: str) -> bool:
        """
        Проверяет валидность адреса Tron.

        Args:
            address: Адрес кошелька.

        Returns:
            bool: True, если адрес валиден, иначе False.
        """
        try:
            return self.client.is_address(address)
        except Exception as e:
            logger.error(f"Address validation failed for {address}: {str(e)}")
            return False

    def get_balance(self, address: str) -> float:
        """
        Получает баланс кошелька в TRX.

        Args:
            address: Адрес кошелька.

        Returns:
            float: Баланс в TRX, 0.0 в случае ошибки.
        """
        try:
            balance = self.client.get_account_balance(address)
            return float(Decimal(balance))
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {str(e)}")
            return 0.0

    def send_transaction(self, private_key: str, to_address: str, amount: float) -> str:
        """
        Отправляет транзакцию TRX.

        Args:
            private_key: Приватный ключ отправителя (hex).
            to_address: Адрес получателя.
            amount: Сумма в TRX.

        Returns:
            str: TXID транзакции.

        Raises:
            ValueError: Если параметры некорректны.
            RuntimeError: Если транзакция не удалась.
        """
        try:
            priv_key = PrivateKey(bytes.fromhex(private_key))
            amount_sun = int(amount * 1_000_000)  # Конвертация в SUN

            txn = (
                self.client.trx.transfer(
                    priv_key.public_key.to_base58check_address(),
                    to_address,
                    amount_sun,
                )
                .build()
                .sign(priv_key)
            )

            txid = txn.txid
            txn.broadcast()
            logger.info(f"Transaction sent: TXID={txid}, to={to_address}, amount={amount} TRX")
            return txid

        except ValueError as e:
            logger.error(f"Invalid transaction parameters: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise RuntimeError(f"Transaction failed: {str(e)}")

    def estimate_bandwidth_usage(self, address: str) -> int:
        """
        Оценивает доступную пропускную способность (bandwidth) кошелька.

        Args:
            address: Адрес кошелька.

        Returns:
            int: Остаток bandwidth (0 в случае ошибки).
        """
        try:
            account = self.client.get_account(address)
            usage = account.get("free_net_usage", -1)
            if usage == -1:
                return 600
            return 600 - usage
        except Exception as e:
            logger.error(f"Bandwidth check failed for {address}: {str(e)}")
            return 0
