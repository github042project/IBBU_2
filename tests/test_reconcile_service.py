"""Unit tests for the Reconciliation service in IB Wallet."""

import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from models.account import Account, AccountType
from services.reconcile import ReconciliationError, reconcile_user_accounts
from tests.golden.testdata import GOLDEN_SCENARIOS
from tests.golden.utils import seed_scenario_state


def _find_scenario(name: str):
    return next(s for s in GOLDEN_SCENARIOS if s.name == name)


def test_reconcile_service_successful_golden_scenario(test_db_session: Session) -> None:
    scenario = _find_scenario("successful_reconciliation")
    seed_scenario_state(test_db_session, scenario)

    result = reconcile_user_accounts(db=test_db_session, user_id=100)

    assert result == scenario.expectation.expected_reconcile_result


def test_reconcile_service_failed_ledger_drift_golden_scenario(test_db_session: Session) -> None:
    scenario = _find_scenario("failed_reconciliation_ledger_drift")
    seed_scenario_state(test_db_session, scenario)

    with pytest.raises(ReconciliationError, match="Balance mismatch for pot"):
        reconcile_user_accounts(db=test_db_session, user_id=100)


def test_reconcile_service_closed_pot_with_balance_raises(test_db_session: Session) -> None:
    closed_pot = Account(
        id=10,
        user_id=100,
        account_type=AccountType.POT,
        currency="INR",
        name="Closed NonZero",
        balance=Decimal("10.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=datetime(2026, 1, 2, 0, 0, 0),
    )
    test_db_session.add(closed_pot)
    test_db_session.flush()

    with pytest.raises(ReconciliationError, match="Closed pot 10 has a non-zero balance"):
        reconcile_user_accounts(db=test_db_session, user_id=100)
