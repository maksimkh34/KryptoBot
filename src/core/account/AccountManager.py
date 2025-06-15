from typing import List

import src.util.logger
from src.core.account import Account
from src.config.files import get_accounts_filename
from src.core.account.json_coder import AccountEncoder, AccountDecoder
from src.core.currency.Amount import Amount
from src.core.exceptions.AccountIsBlocked import AccountIsBlocked
from src.core.exceptions.AccountNotFound import AccountNotFound
from src.database.JsonFileStorage import JsonFileStorage
from src.config.env.env import get_env_var
from src.config.env.var_names import ADMIN_ID
from src.core.is_admin import is_admin

logger = src.util.logger.logger

MAX_DEPT = 5

class AccountManager:
    def __init__(self, storage: JsonFileStorage = None):
        self.storage = storage or JsonFileStorage(
            file_path=get_accounts_filename(),
            default_value=[],
            decode_hook=AccountDecoder.decode_hook,
            encoder=AccountEncoder
        )
        self.accounts: List[Account] = self.storage.data
        logger.debug(f"AccountManager loaded. {len(self.accounts)} accounts")

    def find_account(self, tg_id: int) -> Account:
        for account in self.accounts:
            if account.get_id() == tg_id:
                return account
        logger.log(f"Account with tg_id={tg_id} not found")
        return None

    def block(self, tg_id):
        account = self.find_account(tg_id)
        account.block()
        self.storage.data = self.accounts
        logger.log(f"{tg_id} is blocked.")

    def unblock(self, tg_id):
        account = self.find_account(tg_id)
        account.unblock()
        self.storage.data = self.accounts
        logger.log(f"{tg_id} is blocked.")

    def is_blocked(self, tg_id):
        return self.find_account(tg_id).is_blocked()

    def get_byn_balance(self, tg_id):
        if is_admin(tg_id):
            return -1
        return self.find_account(tg_id).get_balance()

    def add_account(self, tg_id: int, init_balance: int = 0, is_blocked: bool = False) -> Account:
        if self.find_account(tg_id):
            logger.error(f"Account with tg_id={tg_id} already exists")
            raise ValueError(f"Account with tg_id={tg_id} already exists")

        account = Account.Account(tg_id=tg_id, init_balance=init_balance, is_blocked=is_blocked)
        self.accounts.append(account)
        self.storage.data = self.accounts
        logger.info(f"Account created: {account}")
        return account

    def transfer(self, from_tg_id: int, to_tg_id: int, amount: Amount) -> bool:
        logger.debug(f"Creating transaction for {amount.get_byn_amount()} from {from_tg_id} to {to_tg_id}")


        to_account = self.find_account(to_tg_id)

        if type(to_account) is not Account.Account:
            logger.error(f"Transaction receiver [id {to_tg_id}] not found. ")
            raise AccountNotFound(f"Account [id {to_tg_id}] not found. ")

        if to_account.is_blocked():
            logger.error(f"Transaction sender [id {to_tg_id}] is blocked. ")
            raise AccountIsBlocked(f"Transaction sender [id {to_tg_id}] is blocked. ")


        if not is_admin(from_tg_id):
            from_account = self.find_account(from_tg_id)

            if type(from_account) is not Account.Account:
                logger.error(f"Transaction sender [id {from_tg_id}] not found. ")
                raise AccountNotFound(f"Account [id {from_tg_id}] not found. ")

            if from_account.is_blocked():
                logger.error(f"Transaction sender [id {from_tg_id}] is blocked. ")
                raise AccountIsBlocked(f"Transaction sender [id {from_tg_id}] is blocked. ")

            if from_account.get_balance() - amount.get_byn_amount() < MAX_DEPT * -1:
                logger.error(f"Account {from_tg_id} tried to transfer {amount} while balance "
                             f"is {from_account.get_balance()}")
                return False

            if amount.get_byn_amount() <= 0:
                logger.error(f"Invalid amount: {amount.get_byn_amount()}")
                raise ValueError(f"Invalid amount: {amount.get_byn_amount()}")


            from_account.modify_balance(-1 * amount.get_byn_amount())

        to_account.modify_balance(amount.get_byn_amount())
        self.storage.data = self.accounts
        logger.info(f"Transferred {amount} from {from_tg_id} to {to_tg_id}")
        return True


account_manager = AccountManager()
