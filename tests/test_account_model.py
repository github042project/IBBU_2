"""Unit tests for the Account model in IB Wallet."""

from datetime import datetime
from decimal import Decimal

from models.account import Account, AccountType


def test_account_repr_contains_key_fields() -> None:
    account = Account(
        id=1,
        user_id=42,
        account_type=AccountType.POT,
        currency="INR",
        name="Emergency",
        balance=Decimal("100.00"),
        target_amount=Decimal("200.00"),
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )

    repr_text = repr(account)

    assert "Account(" in repr_text
    assert "id=1" in repr_text
    assert "account_type=AccountType.POT" in repr_text
    assert "currency=INR" in repr_text
    assert "balance=100.00" in repr_text


def test_account_open_closed_flags() -> None:
    open_account = Account(
        id=1,
        user_id=1,
        account_type=AccountType.POT,
        currency="INR",
        name="Open",
        balance=Decimal("0.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    closed_account = Account(
        id=2,
        user_id=1,
        account_type=AccountType.POT,
        currency="INR",
        name="Closed",
        balance=Decimal("0.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=datetime(2026, 1, 2, 0, 0, 0),
    )

    assert open_account.is_open()
    assert not open_account.is_closed()
    assert not closed_account.is_open()
    assert closed_account.is_closed()
