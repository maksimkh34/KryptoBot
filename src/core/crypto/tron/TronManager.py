from enum import Enum
from typing import List, Optional
from src.core.crypto.tron.TronClient import TronClient, get_fee
from src.core.crypto.tron.TronWallet import TronWallet
from src.core.currency.Amount import Amount
from src.database.JsonFileStorage import JsonFileStorage
from src.util.logger import logger
import src.core.crypto.tron.json_coder

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
        self.wallets: List[TronWallet] = self.storage.data
        self.client = TronClient()

    def get_wallet_with_lower_reminder(self, wallets: List[TronWallet], amount: Amount) -> Optional[TronWallet]:
        trx_amount = amount.get_to_trx()
        best_wallet = None
        min_reminder = float('inf')

        for wallet in wallets:
            balance = self.client.get_balance(wallet.get_address())
            reminder = balance - trx_amount
            if reminder < min_reminder:
                min_reminder = reminder
                best_wallet = wallet

        return best_wallet

    def pay(self, address: str, amount: Amount) -> PayResult:
        trx_amount = amount.get_to_trx()
        logger.info(f"Initiating payment of {trx_amount:.6f} TRX to {address}")

        try:
            chosen_wallet, fee_charged = self.choose_wallet(amount)
        except ValueError:
            return PayResult.NOT_ENOUGH_BALANCE

        if chosen_wallet is None:
            logger.error("A wallet should have been selected, but was not. This indicates a logic error.")
            return PayResult.ERROR

        logger.debug(f"Chosen wallet {chosen_wallet.get_address()} for the transaction.")

        try:
            self.client.transfer(chosen_wallet.get_private_key(), address, amount)
            return PayResult.COMPLETED_FEE if fee_charged == Amount() else PayResult.COMPLETED
        except Exception as e:
            logger.error(f"An unexpected error occurred during transfer: {e}")
            return PayResult.ERROR

    def choose_wallet(self, amount: Amount) -> (TronWallet, Amount):
        trx_amount = amount.get_to_trx()
        sufficient_wallets = [
            wallet for wallet in self.wallets
            if self.client.get_balance(wallet.get_address()) >= trx_amount
        ]

        if not sufficient_wallets:
            logger.warning(f"Payment failed: Not enough balance on any wallet to send {trx_amount:.6f} TRX.")
            raise ValueError("Not enough balance!")

        no_fees_wallets = self.get_no_fees_wallets(sufficient_wallets)

        if no_fees_wallets:
            return self.get_wallet_with_lower_reminder(no_fees_wallets, amount), Amount()
        else:
            logger.warning(
                "No wallets with enough bandwidth. A fee will be charged. Selecting from all sufficient wallets.")
            return self.get_wallet_with_lower_reminder(sufficient_wallets, amount), get_fee()

    def get_no_fees_wallets(self, wallets: List[TronWallet]) -> List[TronWallet]:
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
