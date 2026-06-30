"""
Services for IB Wallet - reconciliation.

Provides checks to ensure pot and ledger consistency for a given user.
"""

from decimal import Decimal
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.account import Account, AccountType
from models.ledger_entry import LedgerEntry


class ReconciliationError(Exception):
    """Raised when account or ledger reconciliation fails."""


def reconcile_user_accounts(db: Session, user_id: int) -> dict:
    """
    Verify that open pots are valid and closed pots are zero-balanced.

    This function also verifies ledger consistency for pot accounts by
    comparing each pot's current balance with the net result of ledger
    entries that affect that pot.
    """
    pot_accounts = db.scalars(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == AccountType.POT,
        )
    ).all()

    errors: List[str] = []
    open_pots = 0
    closed_pots = 0

    for pot in pot_accounts:
        if pot.closed_at is None:
            open_pots += 1
        else:
            closed_pots += 1
            if pot.balance != Decimal("0"):
                errors.append(
                    f"Closed pot {pot.id} has a non-zero balance: {pot.balance}."
                )

        credit_total = db.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.credit_account_id == pot.id
            )
        )
        debit_total = db.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.debit_account_id == pot.id
            )
        )

        credit_total = Decimal(str(credit_total)) if credit_total is not None else Decimal("0")
        debit_total = Decimal(str(debit_total)) if debit_total is not None else Decimal("0")
        ledger_balance = credit_total - debit_total

        if ledger_balance != pot.balance:
            errors.append(
                f"Balance mismatch for pot {pot.id}: ledger={ledger_balance}, account={pot.balance}."
            )

    if errors:
        raise ReconciliationError("; ".join(errors))

    return {
        "user_id": user_id,
        "open_pots": open_pots,
        "closed_pots": closed_pots,
        "checked_pots": len(pot_accounts),
        "status": "ok",
    }
