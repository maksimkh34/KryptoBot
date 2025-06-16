from decimal import Decimal
from enum import Enum
from typing import List

from src.core.crypto.tron.TronClient import TronClient
from src.core.crypto.tron.TronWallet import TronWallet
from src.core.currency.Amount import Amount
from src.database.JsonFileStorage import JsonFileStorage
import src
from src.util.logger import logger


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
                wallets_new[wallet] = self.client.get_balance(wallet.get_address()) - float(amount.get_to_trx())
                if wallets_new[wallet] < min_reminder:
                    min_reminder = wallets_new[wallet]

        for (wallet, reminder) in wallets_new.items():
            if reminder == min_reminder:
                return wallet

        return None

    def pay(self, address: str, amount: Amount) -> PayResult:
        trx_amount = amount.get_to_trx()

        sufficient_wallets = [
            wallet for wallet in self.wallets
            if self.client.get_balance(wallet.get_address()) >= trx_amount
        ]

        if not sufficient_wallets:
            return PayResult.NOT_ENOUGH_BALANCE

        no_fees_wallets = self.get_no_fees_wallets(sufficient_wallets)
        fee_wallets = [w for w in sufficient_wallets if w not in no_fees_wallets]

        chosen_wallet = None
        fee = False

        if no_fees_wallets:
            chosen_wallet = min(
                no_fees_wallets,
                key=lambda w: self.client.get_balance(w.get_address()) - float(trx_amount)
            )
            fee = False
        elif fee_wallets:
            chosen_wallet = min(
                fee_wallets,
                key=lambda w: self.client.get_balance(w.get_address()) - float(trx_amount)
            )
            fee = True

        if chosen_wallet is None:
            return PayResult.ERROR

        try:
            self.client.transfer(chosen_wallet.get_private_key(), address, amount)
            return PayResult.COMPLETED_FEE if fee else PayResult.COMPLETED
        except Exception as e:
            logger.error("Error transferring: " + str(e.args))
            return PayResult.ERROR

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
