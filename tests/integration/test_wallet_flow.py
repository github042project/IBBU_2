from decimal import Decimal

from sqlalchemy.orm import Session

from aipa.contracts import WalletAction
from models.account import Account
from models.ledger_entry import LedgerEntry
from tests.integration.helpers import dispatch_service, seed_balance_account


def test_wallet_flow_create_list_allocate_withdraw_move_close_and_reconcile(test_db_session: Session) -> None:
    seed_balance_account(test_db_session, 11, balance=Decimal("200.00"), name="Source")
    seed_balance_account(test_db_session, 12, balance=Decimal("0.00"), name="Destination")

    created = dispatch_service(
        test_db_session,
        WalletAction.CREATE_POT,
        {"currency": "INR", "name": "Rainy Day", "target_amount": "100.00"},
    )
    pot = created.result
    assert created.status == "ok"
    assert pot.balance == Decimal("0")

    second_pot = dispatch_service(
        test_db_session,
        WalletAction.CREATE_POT,
        {"currency": "INR", "name": "Emergency"},
    ).result

    listed = dispatch_service(test_db_session, WalletAction.LIST_POTS, {})
    assert listed.status == "ok"
    assert {item.id for item in listed.result} == {pot.id, second_pot.id}

    allocated = dispatch_service(
        test_db_session,
        WalletAction.ALLOCATE,
        {
            "pot_id": pot.id,
            "source_account_id": 11,
            "amount": "80.00",
            "idempotency_key": "wallet-alloc-1",
        },
    )
    assert allocated.status == "ok"
    assert test_db_session.get(Account, pot.id).balance == Decimal("80.00")

    duplicate = dispatch_service(
        test_db_session,
        WalletAction.ALLOCATE,
        {
            "pot_id": pot.id,
            "source_account_id": 11,
            "amount": "80.00",
            "idempotency_key": "wallet-alloc-1",
        },
    )
    assert duplicate.status == "error"
    assert "already exists" in duplicate.error
    assert test_db_session.query(LedgerEntry).count() == 1

    withdrawn = dispatch_service(
        test_db_session,
        WalletAction.WITHDRAW,
        {
            "pot_id": pot.id,
            "destination_account_id": 12,
            "amount": "30.00",
            "idempotency_key": "wallet-withdraw-1",
        },
    )
    assert withdrawn.status == "ok"

    moved = dispatch_service(
        test_db_session,
        WalletAction.MOVE,
        {
            "pot_id": pot.id,
            "destination_pot_id": second_pot.id,
            "amount": "20.00",
            "idempotency_key": "wallet-move-1",
        },
    )
    assert moved.status == "ok"

    emptied = dispatch_service(
        test_db_session,
        WalletAction.WITHDRAW,
        {
            "pot_id": pot.id,
            "destination_account_id": 12,
            "amount": "30.00",
            "idempotency_key": "wallet-withdraw-2",
        },
    )
    assert emptied.status == "ok"

    closed = dispatch_service(test_db_session, WalletAction.CLOSE_POT, {"pot_id": pot.id})
    assert closed.status == "ok"
    assert closed.result.closed_at is not None

    reconciled = dispatch_service(test_db_session, WalletAction.RECONCILE, {})
    assert reconciled.status == "ok"
    assert reconciled.result["status"] == "ok"
    assert reconciled.result["checked_pots"] == 2
