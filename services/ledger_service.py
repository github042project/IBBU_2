"""
Services for IB Wallet - Ledger Service module.

Provides business logic for ledger entry operations.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.account import Account
from models.ledger_entry import LedgerEntry


class LedgerEntryError(Exception):
    """Base exception for ledger service failures."""


class LedgerEntryAlreadyExistsError(LedgerEntryError):
    """Raised when attempting to post a ledger entry with a duplicate idempotency key."""


class AccountNotFoundError(LedgerEntryError):
    """Raised when a referenced account cannot be found."""


class InsufficientFundsError(LedgerEntryError):
    """Raised when the debit account has insufficient funds."""


class CurrencyMismatchError(LedgerEntryError):
    """Raised when account currencies do not match transaction currency."""


class AccountClosedError(LedgerEntryError):
    """Raised when a closed account is referenced in a ledger transaction."""


def _get_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise AccountNotFoundError(f"Account {account_id} does not exist.")
    return account


def _validate_account_for_entry(account: Account, currency: str) -> None:
    if account.closed_at is not None:
        raise AccountClosedError(f"Account {account.id} is closed.")
    if account.currency != currency:
        raise CurrencyMismatchError(
            f"Account {account.id} currency '{account.currency}' does not match '{currency}'."
        )


def _validate_sufficient_funds(account: Account, amount: Decimal) -> None:
    if account.balance < amount:
        raise InsufficientFundsError(
            f"Account {account.id} has insufficient funds for amount {amount}."
        )


def post_entry(
    db: Session,
    debit_account_id: int,
    credit_account_id: int,
    amount: Decimal,
    currency: str,
    idempotency_key: str,
) -> LedgerEntry:
    """
    Post a double-entry ledger transaction.

    Args:
        db: SQLAlchemy session for database operations
        debit_account_id: ID of the account to debit (source account)
        credit_account_id: ID of the account to credit (destination account)
        amount: Transaction amount as Decimal
        currency: ISO 4217 currency code (e.g., INR, CHF)
        idempotency_key: Unique key for idempotent request handling

    Returns:
        The created LedgerEntry object.

    Raises:
        LedgerEntryAlreadyExistsError: If an entry with the same idempotency_key exists
        AccountNotFoundError: If either account cannot be found
        AccountClosedError: If either account is closed
        CurrencyMismatchError: If account currencies do not match the transaction currency
        InsufficientFundsError: If the debit account has insufficient funds
        ValueError: If amount is not greater than zero
    """
    if amount <= Decimal("0"):
        raise ValueError("Amount must be greater than zero.")

    existing_entry = db.execute(
        select(LedgerEntry).where(LedgerEntry.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing_entry is not None:
        raise LedgerEntryAlreadyExistsError(
            f"Ledger entry with idempotency key '{idempotency_key}' already exists."
        )

    debit_account = _get_account(db, debit_account_id)
    credit_account = _get_account(db, credit_account_id)

    _validate_account_for_entry(debit_account, currency)
    _validate_account_for_entry(credit_account, currency)
    _validate_sufficient_funds(debit_account, amount)

    ledger_entry = LedgerEntry(
        debit_account_id=debit_account_id,
        credit_account_id=credit_account_id,
        amount=amount,
        currency=currency,
        idempotency_key=idempotency_key,
    )

    debit_account.balance -= amount
    credit_account.balance += amount

    db.add(ledger_entry)
    db.flush()
    return ledger_entry
