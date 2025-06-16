from typing import List, Optional
from decimal import Decimal

import src.util.logger
from src.core.account.Account import Account
from src.config.files import get_accounts_filename
from src.core.account.json_coder import AccountEncoder, AccountDecoder
from src.core.currency.Amount import Amount
from src.core.exceptions.AccountIsBlocked import AccountIsBlocked
from src.core.exceptions.AccountNotFound import AccountNotFound
from src.database.JsonFileStorage import JsonFileStorage
from src.core.is_admin import is_admin
import src.util.configs

logger = src.util.logger.logger


def get_max_debt() -> Decimal:
    # Загружаем из конфига, если есть, иначе значение по умолчанию
    max_debt_val = src.util.configs.trx_config.data.get('max_debt', -5)
    return Decimal(str(max_debt_val))


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

    def find_account(self, tg_id: int) -> Optional[Account]:
        for account in self.accounts:
            if account.get_id() == tg_id:
                return account
        return None

    def block(self, tg_id: int):
        account = self.find_account(tg_id)
        if account:
            account.block()
            self.storage.data = self.accounts
            logger.log(f"Account {tg_id} is blocked.")
        else:
            logger.warning(f"Attempted to block non-existent account {tg_id}.")

    def unblock(self, tg_id: int):
        account = self.find_account(tg_id)
        if account:
            account.unblock()
            self.storage.data = self.accounts
            logger.log(f"Account {tg_id} is unblocked.")
        else:
            logger.warning(f"Attempted to unblock non-existent account {tg_id}.")

    def get_byn_balance(self, tg_id: int) -> Decimal:
        if is_admin(tg_id):
            return Decimal('999999999.99')
        account = self.find_account(tg_id)
        if account:
            return account.get_balance()  # Возвращает Decimal
        return Decimal('0.0')

    def add_account(self, tg_id: int, init_balance: Decimal = Decimal('0.0'), is_blocked: bool = True) -> Account:
        if self.find_account(tg_id):
            logger.error(f"Account with tg_id={tg_id} already exists")
            raise ValueError(f"Account with tg_id={tg_id} already exists")

        # Используем Decimal для баланса
        account = Account(tg_id=tg_id, init_balance=init_balance, is_blocked=is_blocked)
        self.accounts.append(account)
        self.storage.data = self.accounts
        logger.info(f"Account created: {account}")
        return account

    def transfer(self, from_tg_id: int, to_tg_id: int, amount: Amount) -> bool:
        logger.debug(f"Creating transaction for {amount} from {from_tg_id} to {to_tg_id}")

        from_account = self.find_account(from_tg_id)
        to_account = self.find_account(to_tg_id)

        if to_account is None:
            # Создаем аккаунт получателя, если его нет. Он будет заблокирован.
            to_account = self.add_account(to_tg_id)

        if not is_admin(from_tg_id):
            if from_account is None:
                raise AccountNotFound(f"Account [id {from_tg_id}] not found.")
            if from_account.is_blocked():
                raise AccountIsBlocked(f"Transaction sender [id {from_tg_id}] is blocked.")
            if from_account.get_balance() - amount.get_byn_amount() < get_max_debt():
                logger.error(f"Account {from_tg_id} has insufficient funds for transfer of {amount}.")
                return False

            from_account.modify_balance(-amount.get_byn_amount())

        to_account.modify_balance(amount.get_byn_amount())
        self.storage.data = self.accounts
        logger.info(f"Transferred {amount} from {from_tg_id} to {to_tg_id}")
        return True

    def can_pay(self, tg_id: int, amount: Amount) -> bool:
        if is_admin(tg_id):
            return True
        account = self.find_account(tg_id)
        if not account:
            return False
        return account.get_balance() - amount.get_byn_amount() >= get_max_debt()

    def subtract_from_balance(self, tg_id: int, amount: Amount) -> bool:
        """
        Атомарно проверяет баланс и списывает средства.
        Возвращает True в случае успеха, False если средств недостаточно.
        """
        if is_admin(tg_id):
            return True  # Администратор может все

        account = self.find_account(tg_id)
        if not account:
            logger.warning(f"Attempt to subtract balance from non-existent account {tg_id}")
            return False

        if not self.can_pay(tg_id, amount):
            logger.warning(f"Insufficient funds for {tg_id} to pay {amount}. Balance: {account.get_balance()}")
            return False

        account.modify_balance(-1 * amount.get_byn_amount())
        self.storage.data = self.accounts
        logger.info(f"Subtracted {amount} from {tg_id}. New balance: {account.get_balance()}")
        return True


account_manager = AccountManager()
