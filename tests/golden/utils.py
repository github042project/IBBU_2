"""Shared utilities for golden wallet test scenarios."""

from __future__ import annotations

from datetime import datetime
from typing import Tuple

from sqlalchemy.orm import Session

from models.account import Account
from models.ledger_entry import LedgerEntry
from tests.golden.testdata import AccountSnapshot, GoldenScenario, LedgerEntrySnapshot


def seed_account_snapshots(db: Session, snapshots: Tuple[AccountSnapshot, ...]) -> None:
    for snapshot in snapshots:
        account = Account(
            id=snapshot.id,
            user_id=snapshot.user_id,
            account_type=snapshot.account_type,
            currency=snapshot.currency,
            name=snapshot.name,
            balance=snapshot.balance,
            target_amount=snapshot.target_amount,
            created_at=datetime(2026, 1, 1, 0, 0, 0),
            closed_at=snapshot.closed_at,
        )
        db.add(account)
    db.flush()


def seed_ledger_entry_snapshots(db: Session, snapshots: Tuple[LedgerEntrySnapshot, ...]) -> None:
    for snapshot in snapshots:
        entry = LedgerEntry(
            debit_account_id=snapshot.debit_account_id,
            credit_account_id=snapshot.credit_account_id,
            amount=snapshot.amount,
            currency=snapshot.currency,
            idempotency_key=snapshot.idempotency_key,
            created_at=snapshot.created_at or datetime(2026, 1, 1, 0, 0, 0),
        )
        db.add(entry)
    db.flush()


def seed_scenario_state(db: Session, scenario: GoldenScenario) -> None:
    seed_account_snapshots(db, scenario.initial_accounts)
    seed_ledger_entry_snapshots(db, scenario.initial_ledger_entries)
