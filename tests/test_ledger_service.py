"""Unit tests for the Ledger service in IB Wallet."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from models.account import Account, AccountType
from models.ledger_entry import LedgerEntry
from services.ledger_service import (
    AccountClosedError,
    AccountNotFoundError,
    CurrencyMismatchError,
    InsufficientFundsError,
    LedgerEntryAlreadyExistsError,
    post_entry,
)


def test_post_entry_success_updates_balances(test_db_session: Session) -> None:
    source = Account(
        id=1,
        user_id=1,
        account_type=AccountType.BALANCE,
        currency="INR",
        name="Source",
        balance=Decimal("100.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    destination = Account(
        id=2,
        user_id=1,
        account_type=AccountType.POT,
        currency="INR",
        name="Pot",
        balance=Decimal("0.00"),
        target_amount=Decimal("200.00"),
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    test_db_session.add_all([source, destination])
    test_db_session.flush()

    entry = post_entry(
        db=test_db_session,
        debit_account_id=1,
        credit_account_id=2,
        amount=Decimal("50.00"),
        currency="INR",
        idempotency_key="entry-001",
    )

    assert entry.debit_account_id == 1
    assert entry.credit_account_id == 2
    assert entry.amount == Decimal("50.00")
    assert entry.currency == "INR"

    assert test_db_session.get(Account, 1).balance == Decimal("50.00")
    assert test_db_session.get(Account, 2).balance == Decimal("50.00")


def test_post_entry_duplicate_idempotency_key_raises(test_db_session: Session) -> None:
    source = Account(
        id=1,
        user_id=1,
        account_type=AccountType.BALANCE,
        currency="INR",
        name="Source",
        balance=Decimal("100.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    destination = Account(
        id=2,
        user_id=1,
        account_type=AccountType.POT,
        currency="INR",
        name="Pot",
        balance=Decimal("0.00"),
        target_amount=Decimal("200.00"),
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    test_db_session.add_all([source, destination])
    test_db_session.flush()

    post_entry(
        db=test_db_session,
        debit_account_id=1,
        credit_account_id=2,
        amount=Decimal("10.00"),
        currency="INR",
        idempotency_key="duplicate-001",
    )

    with pytest.raises(LedgerEntryAlreadyExistsError, match="already exists"):
        post_entry(
            db=test_db_session,
            debit_account_id=1,
            credit_account_id=2,
            amount=Decimal("10.00"),
            currency="INR",
            idempotency_key="duplicate-001",
        )


def test_post_entry_insufficient_funds_raises(test_db_session: Session) -> None:
    source = Account(
        id=1,
        user_id=1,
        account_type=AccountType.BALANCE,
        currency="INR",
        name="Source",
        balance=Decimal("10.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    destination = Account(
        id=2,
        user_id=1,
        account_type=AccountType.POT,
        currency="INR",
        name="Pot",
        balance=Decimal("0.00"),
        target_amount=Decimal("200.00"),
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    test_db_session.add_all([source, destination])
    test_db_session.flush()

    with pytest.raises(InsufficientFundsError, match="insufficient funds"):
        post_entry(
            db=test_db_session,
            debit_account_id=1,
            credit_account_id=2,
            amount=Decimal("20.00"),
            currency="INR",
            idempotency_key="insufficient-001",
        )


def test_post_entry_currency_mismatch_raises(test_db_session: Session) -> None:
    source = Account(
        id=1,
        user_id=1,
        account_type=AccountType.BALANCE,
        currency="CHF",
        name="Source",
        balance=Decimal("100.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    destination = Account(
        id=2,
        user_id=1,
        account_type=AccountType.POT,
        currency="INR",
        name="Pot",
        balance=Decimal("0.00"),
        target_amount=Decimal("200.00"),
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    test_db_session.add_all([source, destination])
    test_db_session.flush()

    with pytest.raises(CurrencyMismatchError, match="does not match"):
        post_entry(
            db=test_db_session,
            debit_account_id=1,
            credit_account_id=2,
            amount=Decimal("10.00"),
            currency="CHF",
            idempotency_key="currency-001",
        )


def test_post_entry_closed_account_raises(test_db_session: Session) -> None:
    source = Account(
        id=1,
        user_id=1,
        account_type=AccountType.BALANCE,
        currency="INR",
        name="Source",
        balance=Decimal("100.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=datetime(2026, 1, 1, 0, 0, 0),
    )
    destination = Account(
        id=2,
        user_id=1,
        account_type=AccountType.POT,
        currency="INR",
        name="Pot",
        balance=Decimal("0.00"),
        target_amount=Decimal("200.00"),
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    test_db_session.add_all([source, destination])
    test_db_session.flush()

    with pytest.raises(AccountClosedError, match="closed"):
        post_entry(
            db=test_db_session,
            debit_account_id=1,
            credit_account_id=2,
            amount=Decimal("10.00"),
            currency="INR",
            idempotency_key="closed-001",
        )


def test_post_entry_account_not_found_raises(test_db_session: Session) -> None:
    with pytest.raises(AccountNotFoundError, match="does not exist"):
        post_entry(
            db=test_db_session,
            debit_account_id=999,
            credit_account_id=888,
            amount=Decimal("10.00"),
            currency="INR",
            idempotency_key="missing-001",
        )
