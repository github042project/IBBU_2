"""
Services for IB Wallet - Pot operations.

Contains pot creation, allocation, withdrawal, transfer, and close behavior.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from money import Money
from models.account import Account, AccountType
from services.ledger_service import (
    AccountNotFoundError,
    LedgerEntryError,
    post_entry,
)


class PotServiceError(Exception):
    """Base exception for pot service failures."""


class PotNotFoundError(PotServiceError):
    """Raised when a pot account cannot be found."""


class PotClosedError(PotServiceError):
    """Raised when an operation targets a closed pot."""


class PotValidationError(PotServiceError):
    """Raised when pot input validation fails."""


def create_pot(
    db: Session,
    user_id: int,
    currency: str,
    name: str,
    target_amount: Optional[Decimal] = None,
) -> Account:
    """
    Create a new pot account for a user.

    Args:
        db: SQLAlchemy session
        user_id: User identifier
        currency: ISO 4217 currency code (INR or CHF)
        name: Human-readable pot name
        target_amount: Optional target amount for the pot

    Returns:
        The created pot account

    Raises:
        PotValidationError: If input validation fails
    """
    try:
        Money.zero(currency)
    except ValueError as exc:
        raise PotValidationError(str(exc)) from exc

    if target_amount is not None:
        target_value = Money(target_amount, currency)
        if target_value.amount < Decimal("0"):
            raise PotValidationError("Target amount must be non-negative.")

    pot = Account(
        user_id=user_id,
        account_type=AccountType.POT,
        currency=currency,
        name=name,
        balance=Decimal("0"),
        target_amount=target_amount,
        created_at=datetime.now(timezone.utc),
        closed_at=None,
    )

    db.add(pot)
    db.flush()
    return pot


def list_pots(db: Session, user_id: int) -> List[Account]:
    """
    List all pot accounts for a specific user.
    """
    return db.scalars(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == AccountType.POT,
        )
    ).all()


def _get_pot(db: Session, pot_id: int) -> Account:
    pot = db.get(Account, pot_id)
    if pot is None or pot.account_type != AccountType.POT:
        raise PotNotFoundError(f"Pot account {pot_id} was not found.")
    return pot


def _validate_pot_state(pot: Account) -> None:
    if pot.closed_at is not None:
        raise PotClosedError(f"Pot account {pot.id} is already closed.")


def _validate_account_owner(source: Account, target: Account) -> None:
    if source.user_id != target.user_id:
        raise PotValidationError("Account ownership mismatch for pot operation.")


def allocate_to_pot(
    db: Session,
    pot_id: int,
    source_account_id: int,
    amount: Decimal,
    idempotency_key: str,
) -> Account:
    """
    Allocate funds from a source account into a pot.
    """
    pot = _get_pot(db, pot_id)
    _validate_pot_state(pot)

    source_account = db.get(Account, source_account_id)
    if source_account is None:
        raise PotServiceError(
            f"Source account {source_account_id} was not found."
        )

    _validate_account_owner(source_account, pot)

    try:
        post_entry(
            db=db,
            debit_account_id=source_account_id,
            credit_account_id=pot.id,
            amount=amount,
            currency=pot.currency,
            idempotency_key=idempotency_key,
        )
    except LedgerEntryError as exc:
        raise PotServiceError(str(exc)) from exc

    return pot


def withdraw_from_pot(
    db: Session,
    pot_id: int,
    destination_account_id: int,
    amount: Decimal,
    idempotency_key: str,
) -> Account:
    """
    Withdraw funds from a pot into a destination account.
    """
    pot = _get_pot(db, pot_id)
    _validate_pot_state(pot)

    destination_account = db.get(Account, destination_account_id)
    if destination_account is None:
        raise PotServiceError(
            f"Destination account {destination_account_id} was not found."
        )

    _validate_account_owner(destination_account, pot)

    try:
        post_entry(
            db=db,
            debit_account_id=pot.id,
            credit_account_id=destination_account_id,
            amount=amount,
            currency=pot.currency,
            idempotency_key=idempotency_key,
        )
    except LedgerEntryError as exc:
        raise PotServiceError(str(exc)) from exc

    return pot


def move_between_pots(
    db: Session,
    source_pot_id: int,
    destination_pot_id: int,
    amount: Decimal,
    idempotency_key: str,
) -> Account:
    """
    Move funds from one pot to another.
    """
    source_pot = _get_pot(db, source_pot_id)
    destination_pot = _get_pot(db, destination_pot_id)

    _validate_pot_state(source_pot)
    _validate_pot_state(destination_pot)
    _validate_account_owner(source_pot, destination_pot)

    if source_pot.currency != destination_pot.currency:
        raise PotValidationError(
            "Cannot move funds between pots with different currencies."
        )

    try:
        post_entry(
            db=db,
            debit_account_id=source_pot.id,
            credit_account_id=destination_pot.id,
            amount=amount,
            currency=source_pot.currency,
            idempotency_key=idempotency_key,
        )
    except LedgerEntryError as exc:
        raise PotServiceError(str(exc)) from exc

    return destination_pot


def close_pot(db: Session, pot_id: int) -> Account:
    """
    Close a pot account once its balance is zero.
    """
    pot = _get_pot(db, pot_id)
    _validate_pot_state(pot)

    if pot.balance != Decimal("0"):
        raise PotValidationError(
            "Pot must have a zero balance before it can be closed."
        )

    pot.closed_at = datetime.now(timezone.utc)
    db.flush()
    return pot
