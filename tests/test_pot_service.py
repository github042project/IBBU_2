"""Unit tests for the Pot service in IB Wallet."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from models.account import Account, AccountType
from services.pot_service import (
    PotClosedError,
    PotNotFoundError,
    PotServiceError,
    PotValidationError,
    allocate_to_pot,
    close_pot,
    create_pot,
    list_pots,
    move_between_pots,
    withdraw_from_pot,
)
from services.ledger_service import post_entry


def create_account(
    session: Session,
    account_id: int,
    account_type: AccountType,
    balance: Decimal,
    currency: str = "INR",
    name: str = "Account",
    target_amount: Decimal | None = None,
    closed_at=None,
) -> Account:
    account = Account(
        id=account_id,
        user_id=1,
        account_type=account_type,
        currency=currency,
        name=name,
        balance=balance,
        target_amount=target_amount,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=closed_at,
    )
    session.add(account)
    session.flush()
    return account


def test_create_pot_success(test_db_session: Session) -> None:
    pot = create_pot(
        db=test_db_session,
        user_id=1,
        currency="INR",
        name="Rainy Day",
        target_amount=Decimal("500.00"),
    )

    assert pot.id is not None
    assert pot.user_id == 1
    assert pot.account_type == AccountType.POT
    assert pot.currency == "INR"
    assert pot.balance == Decimal("0")
    assert pot.target_amount == Decimal("500.00")
    assert pot.closed_at is None


def test_create_pot_invalid_target_amount_raises(test_db_session: Session) -> None:
    with pytest.raises(PotValidationError, match="non-negative"):
        create_pot(
            db=test_db_session,
            user_id=1,
            currency="INR",
            name="Invalid Target",
            target_amount=Decimal("-1.00"),
        )


def test_list_pots_returns_all_pots(test_db_session: Session) -> None:
    create_pot(db=test_db_session, user_id=1, currency="INR", name="Pot A")
    create_pot(db=test_db_session, user_id=1, currency="INR", name="Pot B")
    create_pot(db=test_db_session, user_id=2, currency="INR", name="Other User")

    pots = list_pots(db=test_db_session, user_id=1)

    assert len(pots) == 2
    assert all(p.user_id == 1 for p in pots)


def test_allocate_to_pot_success(test_db_session: Session) -> None:
    source = create_account(
        test_db_session, 1, AccountType.BALANCE, Decimal("150.00"), name="Main"
    )
    pot = create_pot(db=test_db_session, user_id=1, currency="INR", name="Rainy Day")

    result = allocate_to_pot(
        db=test_db_session,
        pot_id=pot.id,
        source_account_id=source.id,
        amount=Decimal("100.00"),
        idempotency_key="alloc-100",
    )

    assert result.balance == Decimal("100.00")
    assert test_db_session.get(Account, source.id).balance == Decimal("50.00")


def test_allocate_to_pot_invalid_pot_raises(test_db_session: Session) -> None:
    source = create_account(
        test_db_session, 1, AccountType.BALANCE, Decimal("150.00"), name="Main"
    )

    with pytest.raises(Exception, match="Pot account 999 was not found"):
        allocate_to_pot(
            db=test_db_session,
            pot_id=999,
            source_account_id=source.id,
            amount=Decimal("100.00"),
            idempotency_key="alloc-002",
        )


def test_withdraw_from_pot_success(test_db_session: Session) -> None:
    source = create_account(
        test_db_session, 1, AccountType.BALANCE, Decimal("150.00"), name="Main"
    )
    destination = create_account(
        test_db_session, 2, AccountType.BALANCE, Decimal("0.00"), name="Destination"
    )
    pot = create_pot(db=test_db_session, user_id=1, currency="INR", name="Rainy Day")

    allocate_to_pot(
        db=test_db_session,
        pot_id=pot.id,
        source_account_id=source.id,
        amount=Decimal("100.00"),
        idempotency_key="seed-001",
    )

    result = withdraw_from_pot(
        db=test_db_session,
        pot_id=pot.id,
        destination_account_id=destination.id,
        amount=Decimal("70.00"),
        idempotency_key="withdraw-001",
    )

    assert result.balance == Decimal("30.00")
    assert test_db_session.get(Account, destination.id).balance == Decimal("70.00")


def test_withdraw_from_pot_insufficient_balance_raises(test_db_session: Session) -> None:
    source = create_account(
        test_db_session, 1, AccountType.BALANCE, Decimal("50.00"), name="Main"
    )
    destination = create_account(
        test_db_session, 2, AccountType.BALANCE, Decimal("0.00"), name="Destination"
    )
    pot = create_pot(db=test_db_session, user_id=1, currency="INR", name="Pot")

    allocate_to_pot(
        db=test_db_session,
        pot_id=pot.id,
        source_account_id=source.id,
        amount=Decimal("50.00"),
        idempotency_key="seed-002",
    )

    with pytest.raises(PotServiceError, match="insufficient funds"):
        withdraw_from_pot(
            db=test_db_session,
            pot_id=pot.id,
            destination_account_id=destination.id,
            amount=Decimal("100.00"),
            idempotency_key="withdraw-002",
        )


def test_move_between_pots_success(test_db_session: Session) -> None:
    source_account = Account(
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
    test_db_session.add(source_account)
    pot_a = create_pot(db=test_db_session, user_id=1, currency="INR", name="A")
    pot_b = create_pot(db=test_db_session, user_id=1, currency="INR", name="B")
    post_entry(
        db=test_db_session,
        debit_account_id=source_account.id,
        credit_account_id=pot_a.id,
        amount=Decimal("100.00"),
        currency="INR",
        idempotency_key="seed-003",
    )

    result = move_between_pots(
        db=test_db_session,
        source_pot_id=pot_a.id,
        destination_pot_id=pot_b.id,
        amount=Decimal("50.00"),
        idempotency_key="move-001",
    )

    assert result.id == pot_b.id
    assert test_db_session.get(Account, pot_a.id).balance == Decimal("50.00")
    assert test_db_session.get(Account, pot_b.id).balance == Decimal("50.00")


def test_move_between_pots_currency_mismatch_raises(test_db_session: Session) -> None:
    source_account = Account(
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
    test_db_session.add(source_account)
    pot_a = create_pot(db=test_db_session, user_id=1, currency="INR", name="A")
    pot_b = create_pot(db=test_db_session, user_id=1, currency="CHF", name="B")
    post_entry(
        db=test_db_session,
        debit_account_id=source_account.id,
        credit_account_id=pot_a.id,
        amount=Decimal("100.00"),
        currency="INR",
        idempotency_key="seed-004",
    )

    with pytest.raises(PotValidationError, match="different currencies"):
        move_between_pots(
            db=test_db_session,
            source_pot_id=pot_a.id,
            destination_pot_id=pot_b.id,
            amount=Decimal("50.00"),
            idempotency_key="move-002",
        )


def test_close_pot_success(test_db_session: Session) -> None:
    pot = create_pot(db=test_db_session, user_id=1, currency="INR", name="CloseMe")
    result = close_pot(db=test_db_session, pot_id=pot.id)

    assert result.closed_at is not None


def test_close_pot_with_balance_raises(test_db_session: Session) -> None:
    source_account = Account(
        id=1,
        user_id=1,
        account_type=AccountType.BALANCE,
        currency="INR",
        name="Source",
        balance=Decimal("20.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    test_db_session.add(source_account)
    pot = create_pot(db=test_db_session, user_id=1, currency="INR", name="NoClose")
    post_entry(
        db=test_db_session,
        debit_account_id=source_account.id,
        credit_account_id=pot.id,
        amount=Decimal("20.00"),
        currency="INR",
        idempotency_key="seed-005",
    )

    with pytest.raises(PotValidationError, match="zero balance"):
        close_pot(db=test_db_session, pot_id=pot.id)


def test_close_pot_not_found_raises(test_db_session: Session) -> None:
    with pytest.raises(PotNotFoundError, match="was not found"):
        close_pot(db=test_db_session, pot_id=999)
