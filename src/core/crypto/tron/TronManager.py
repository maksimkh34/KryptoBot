from enum import Enum
from typing import List

from src.core.crypto.tron.TronClient import TronClient
from src.core.crypto.tron.TronWallet import TronWallet
from src.core.currency.Amount import Amount
from src.database.JsonFileStorage import JsonFileStorage
import src


class PayResult(Enum):
    COMPLETED = 0
    COMPLETED_FEE = 1
    NOT_ENOUGH_BALANCE = 2
    ERROR = 3

class TronManager:
    def __init__(self):
        self.storage = JsonFileStorage(src.config.files.get_trx_wallets_filename(),
                                       default_value=[],
                                       decode_hook=src.core.crypto.tron.json_coder.TronWalletDecoder.decode_hook,
                                       encoder=src.core.crypto.tron.json_coder.TronWalletEncoder)
        self.wallets = self.storage.data
        self.client = TronClient()

    def get_wallet_with_lower_reminder(self, wallets: List[TronWallet], amount: Amount):
        if len(wallets) == 0:
            return None

        if len(wallets) == 1:
            return wallets[0]


        wallets_new = {}
        min_reminder = 9999999999999999999

        for wallet in wallets:
            if self.client.get_balance(wallet.get_address()) > amount.get_to_trx():
                wallets_new[wallet] = self.client.get_balance(wallet.get_address()) - amount.get_to_trx()
                if wallets_new[wallet] < min_reminder:
                    min_reminder = wallets_new[wallet]

        for (wallet, reminder) in wallets_new.items():
            if reminder == min_reminder:
                return wallet

        return None

    def pay(self, address: str, amount: Amount) -> PayResult:
        _wallets = []

        for wallet in self.storage.data:
            if self.client.get_balance(wallet.get_address()) > amount.get_to_trx():
                _wallets.append(wallet)

        no_fees_wallets = self.get_no_fees_wallets(_wallets)
        fee = False

        if len(no_fees_wallets) == 0:
            wallet = self.get_wallet_with_lower_reminder(_wallets, amount)
            fee = True
        else:
            wallet = self.get_wallet_with_lower_reminder(no_fees_wallets, amount)

        if wallet is None:
            return PayResult.NOT_ENOUGH_BALANCE

        self.client.transfer(wallet.get_private_key(), address, amount)
        return PayResult.COMPLETED_FEE if fee else PayResult.COMPLETED

    def get_no_fees_wallets(self, wallets):
        no_fees_wallets = []
        for wallet in wallets:
            if self.client.can_transfer_without_fees(wallet.get_address()):
                no_fees_wallets.append(wallet)
        return no_fees_wallets

    def can_transfer_without_fees(self):
        return len(self.get_no_fees_wallets(self.storage.data)) > 0

    def get_max_payment_amount(self):
        max_balance = -1
        for wallet in self.storage.data:
            balance = self.client.get_balance(wallet.get_address())
            if balance > max_balance:
                max_balance = balance
        return max_balance

tron_manager = TronManager()
