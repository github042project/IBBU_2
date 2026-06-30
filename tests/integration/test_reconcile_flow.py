from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from models.account import Account, AccountType
from services.ledger_service import post_entry
from services.pot_service import create_pot
from services.reconcile import ReconciliationError, reconcile_user_accounts


def test_reconcile_flow_reports_success_and_failure(test_db_session: Session) -> None:
    source = Account(
        id=21,
        user_id=1,
        account_type=AccountType.BALANCE,
        currency="INR",
        name="Source",
        balance=Decimal("100.00"),
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    test_db_session.add(source)
    test_db_session.flush()

    pot = create_pot(db=test_db_session, user_id=1, currency="INR", name="Reconcile Pot")
    post_entry(
        db=test_db_session,
        debit_account_id=source.id,
        credit_account_id=pot.id,
        amount=Decimal("50.00"),
        currency="INR",
        idempotency_key="reconcile-1",
    )

    result = reconcile_user_accounts(db=test_db_session, user_id=1)
    assert result["status"] == "ok"
    assert result["open_pots"] == 1

    closed_pot = create_pot(db=test_db_session, user_id=1, currency="INR", name="Closed Pot")
    post_entry(
        db=test_db_session,
        debit_account_id=source.id,
        credit_account_id=closed_pot.id,
        amount=Decimal("30.00"),
        currency="INR",
        idempotency_key="reconcile-2",
    )
    closed_pot.closed_at = datetime(2026, 1, 2, 0, 0, 0)
    test_db_session.flush()

    with pytest.raises(ReconciliationError):
        reconcile_user_accounts(db=test_db_session, user_id=1)
