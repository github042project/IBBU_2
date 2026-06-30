"""Unit tests for the Money module in IB Wallet."""

from decimal import Decimal

import pytest

from money import Money


def test_money_zero_returns_zero_amount() -> None:
    zero_money = Money.zero("INR")

    assert zero_money.amount == Decimal("0")
    assert zero_money.currency == "INR"


def test_money_add_same_currency() -> None:
    a = Money("10.00", "INR")
    b = Money("5.50", "INR")

    total = a + b

    assert total == Money("15.50", "INR")


def test_money_subtract_same_currency() -> None:
    a = Money("10.00", "INR")
    b = Money("3.25", "INR")

    result = a - b

    assert result == Money("6.75", "INR")


def test_money_equality_and_comparison() -> None:
    assert Money("10.00", "CHF") == Money("10.00", "CHF")
    assert Money("5.00", "CHF") < Money("7.00", "CHF")
    assert Money("7.00", "CHF") > Money("5.00", "CHF")


def test_money_unsupported_currency_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported currency"):
        Money("10.00", "USD")


def test_money_add_different_currencies_raises() -> None:
    with pytest.raises(ValueError, match="Cannot add different currencies"):
        Money("10.00", "INR") + Money("5.00", "CHF")


def test_money_subtract_different_currencies_raises() -> None:
    with pytest.raises(ValueError, match="Cannot subtract different currencies"):
        Money("10.00", "INR") - Money("5.00", "CHF")


def test_money_invalid_amount_raises() -> None:
    with pytest.raises(ValueError, match="Invalid amount"):
        Money(object(), "INR")


def test_money_zero_and_negative_flags() -> None:
    assert Money("0", "CHF").is_zero()
    assert not Money("0.01", "CHF").is_zero()
    assert Money("-1.00", "INR").is_negative()
    assert not Money("1.00", "INR").is_negative()


def test_money_repr_str_and_to_dict() -> None:
    money = Money("10.50", "INR")

    assert repr(money) == "Money(10.50, 'INR')"
    assert str(money) == "10.50 INR"
    assert money.to_dict() == {"amount": "10.50", "currency": "INR"}


def test_money_comparisons_and_invalid_operand_raises() -> None:
    a = Money("10.00", "CHF")
    b = Money("10.00", "CHF")
    c = Money("5.00", "CHF")

    assert a == b
    assert c < a
    assert a <= b
    assert a >= b
    assert a > c

    with pytest.raises(TypeError):
        _ = a < 5
