from decimal import Decimal

import requests
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider

from src.config.env.env import get_env_var
from src.config.env.var_names import TRON_NETWORK, TRONGRID_API_KEY
from src.core.crypto.Client import Client
from src.core.currency.Amount import Amount
from src.database.JsonFileStorage import JsonFileStorage
import src.config.files
import src.core.crypto.tron.json_coder
from src.util.logger import logger

REQUIRED_BANDWIDTH_TO_TRANSFER = 280
FEE = Amount(0.2714)


def get_fee():
    return FEE


class TronClient(Client):
    def __init__(self):
        self.network = get_env_var(TRON_NETWORK)
        self.api_key = get_env_var(TRONGRID_API_KEY)
        self._client = self._get_client()

    def _get_client(self) -> Tron:
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
            client.get_block(0)
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
        try:
            return self._client.is_address(address)
        except Exception as e:
            logger.error(f"Address validation failed for {address}: {str(e)}")
            return False

    def get_balance(self, address: str) -> float:
        try:
            balance = self._client.get_account_balance(address)
            return float(Decimal(balance))
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {str(e)}")
            return 0.0

    def transfer(self, private_key: str, to_address: str, amount: Amount) -> str:
        try:
            prv_key = PrivateKey(bytes.fromhex(private_key))
            amount_sun = int(amount.get_to_trx() * 1_000_000)  # Конвертация в SUN

            txn = (
                self._client.trx.transfer(
                    prv_key.public_key.to_base58check_address(),
                    to_address,
                    amount_sun,
                )
                .build()
                .sign(prv_key)
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
        try:
            account = self._client.get_account(address)
            usage = account.get("free_net_usage", -1)
            if usage == -1:
                return 600
            return 600 - usage
        except Exception as e:
            logger.error(f"Bandwidth check failed for {address}: {str(e)}")
            return 0

    def can_transfer_without_fees(self, address):
        return self.estimate_bandwidth_usage(address) >= REQUIRED_BANDWIDTH_TO_TRANSFER
