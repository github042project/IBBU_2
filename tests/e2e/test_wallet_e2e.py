from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from aipa.contracts import WalletAction
from models.account import Account
from models.ledger_entry import LedgerEntry
from tests.integration.helpers import guarded_payload, post_aipa_dispatch, seed_balance_account
from vault.consent import ConsentScope, issue_token
from vault.region import Region


def test_wallet_e2e_dispatches_complete_wallet_lifecycle(
    test_app: TestClient,
    test_db_session: Session,
) -> None:
    user_id = 100
    seed_balance_account(test_db_session, 1001, user_id=user_id, balance=Decimal("200.00"), name="Main")
    seed_balance_account(test_db_session, 1002, user_id=user_id, balance=Decimal("0.00"), name="Destination")

    create_response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        guarded_payload(user_id, currency="INR", name="E2E Pot"),
        user_id=user_id,
    )
    assert create_response.status_code == 200
    pot = create_response.json()["result"]

    second_create_response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        guarded_payload(user_id, currency="INR", name="E2E Target"),
        user_id=user_id,
    )
    assert second_create_response.status_code == 200
    second_pot = second_create_response.json()["result"]

    list_response = post_aipa_dispatch(
        test_app,
        WalletAction.LIST_POTS,
        guarded_payload(user_id),
        user_id=user_id,
    )
    assert list_response.status_code == 200
    assert {item["id"] for item in list_response.json()["result"]} == {pot["id"], second_pot["id"]}

    allocate_response = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            source_account_id=1001,
            amount="80.00",
            idempotency_key="e2e-alloc",
        ),
        user_id=user_id,
    )
    assert allocate_response.status_code == 200
    assert allocate_response.json()["status"] == "ok"

    duplicate_response = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            source_account_id=1001,
            amount="80.00",
            idempotency_key="e2e-alloc",
        ),
        user_id=user_id,
    )
    assert duplicate_response.status_code == 409
    assert test_db_session.query(LedgerEntry).count() == 1

    withdraw_response = post_aipa_dispatch(
        test_app,
        WalletAction.WITHDRAW,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            destination_account_id=1002,
            amount="30.00",
            idempotency_key="e2e-withdraw-1",
        ),
        user_id=user_id,
    )
    assert withdraw_response.status_code == 200
    assert withdraw_response.json()["status"] == "ok"

    move_response = post_aipa_dispatch(
        test_app,
        WalletAction.MOVE,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            destination_pot_id=second_pot["id"],
            amount="20.00",
            idempotency_key="e2e-move",
        ),
        user_id=user_id,
    )
    assert move_response.status_code == 200
    assert move_response.json()["status"] == "ok"

    final_withdraw_response = post_aipa_dispatch(
        test_app,
        WalletAction.WITHDRAW,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            destination_account_id=1002,
            amount="30.00",
            idempotency_key="e2e-withdraw-2",
        ),
        user_id=user_id,
    )
    assert final_withdraw_response.status_code == 200
    assert final_withdraw_response.json()["status"] == "ok"

    close_response = post_aipa_dispatch(
        test_app,
        WalletAction.CLOSE_POT,
        guarded_payload(user_id, pot_id=pot["id"]),
        user_id=user_id,
    )
    assert close_response.status_code == 200
    assert close_response.json()["result"]["closed_at"] is not None

    reconcile_response = post_aipa_dispatch(
        test_app,
        WalletAction.RECONCILE,
        guarded_payload(user_id),
        user_id=user_id,
    )
    assert reconcile_response.status_code == 200
    assert reconcile_response.json()["result"]["status"] == "ok"
    assert test_db_session.get(Account, 1001).balance == Decimal("120.00")
    assert test_db_session.get(Account, 1002).balance == Decimal("60.00")


def test_wallet_e2e_rejects_invalid_dispatch_token_and_region(test_app: TestClient) -> None:
    invalid_dispatch = post_aipa_dispatch(test_app, "FLY", {}, user_id=2)
    assert invalid_dispatch.status_code == 422

    invalid_token = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {
            "currency": "INR",
            "name": "Bad Token",
            "token_id": "5b27e027-cc40-45f9-a1f5-000000000000",
            "region": Region.INDIA.value,
        },
        user_id=2,
    )
    assert invalid_token.status_code == 403

    token = issue_token(user_id=2, scope=ConsentScope.WALLET_WRITE.value)
    invalid_region = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {
            "currency": "INR",
            "name": "Bad Region",
            "token_id": str(token.token_id),
            "region": "BRAZIL",
        },
        user_id=2,
    )
    assert invalid_region.status_code == 400
