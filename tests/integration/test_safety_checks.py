from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from aipa.contracts import WalletAction
from models.account import Account
from models.ledger_entry import LedgerEntry
from tests.integration.helpers import guarded_payload, post_aipa_dispatch, seed_balance_account
from vault.consent import ConsentScope, issue_token
from vault.region import Region


def _assert_public_error(response, expected_status: int) -> None:
    assert response.status_code == expected_status
    detail = str(response.json()["detail"])
    assert "Traceback" not in detail
    assert "sqlalchemy" not in detail.lower()


def _create_pot(client: TestClient, user_id: int, name: str = "Safety Pot") -> dict:
    response = post_aipa_dispatch(
        client,
        WalletAction.CREATE_POT,
        guarded_payload(user_id, currency="INR", name=name),
        user_id=user_id,
    )
    assert response.status_code == 200
    return response.json()["result"]


def test_safety_invalid_dispatches_and_malformed_payloads_return_422(test_app: TestClient) -> None:
    unsupported_action = post_aipa_dispatch(test_app, "DELETE_POT", {}, user_id=20)
    _assert_public_error(unsupported_action, 422)

    missing_required_field = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        guarded_payload(20, pot_id=1, amount="10.00", idempotency_key="missing-source"),
        user_id=20,
    )
    _assert_public_error(missing_required_field, 422)

    malformed_payload = test_app.post(
        "/aipa/dispatch",
        json={
            "trace_id": "not-a-uuid",
            "user_id": 20,
            "action": WalletAction.LIST_POTS.value,
            "payload": [],
        },
    )
    _assert_public_error(malformed_payload, 422)


def test_safety_permission_failures_return_403(test_app: TestClient) -> None:
    read_only = issue_token(user_id=21, scope=ConsentScope.WALLET_READ.value)
    read_only_response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {
            "currency": "INR",
            "name": "Read Only",
            "token_id": str(read_only.token_id),
            "region": Region.INDIA.value,
        },
        user_id=21,
    )
    _assert_public_error(read_only_response, 403)

    other_user_token = issue_token(user_id=999, scope=ConsentScope.WALLET_WRITE.value)
    mismatch_response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {
            "currency": "INR",
            "name": "Wrong User",
            "token_id": str(other_user_token.token_id),
            "region": Region.INDIA.value,
        },
        user_id=21,
    )
    _assert_public_error(mismatch_response, 403)


def test_safety_invalid_region_and_missing_accounts_return_expected_statuses(
    test_app: TestClient,
    test_db_session: Session,
) -> None:
    user_id = 22
    seed_balance_account(test_db_session, 2201, user_id=user_id, balance=Decimal("100.00"))
    pot = _create_pot(test_app, user_id)

    token = issue_token(user_id=user_id, scope=ConsentScope.WALLET_WRITE.value)
    invalid_region = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        {
            "pot_id": pot["id"],
            "source_account_id": 2201,
            "amount": "10.00",
            "idempotency_key": "bad-region",
            "token_id": str(token.token_id),
            "region": "BRAZIL",
        },
        user_id=user_id,
    )
    _assert_public_error(invalid_region, 400)

    missing_source = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            source_account_id=99999,
            amount="10.00",
            idempotency_key="missing-source-account",
        ),
        user_id=user_id,
    )
    _assert_public_error(missing_source, 404)
    assert test_db_session.get(Account, pot["id"]).balance == Decimal("0.00")


def test_safety_duplicate_dispatch_invalid_amounts_and_closed_accounts_preserve_invariants(
    test_app: TestClient,
    test_db_session: Session,
) -> None:
    user_id = 23
    source = seed_balance_account(test_db_session, 2301, user_id=user_id, balance=Decimal("100.00"))
    destination = seed_balance_account(test_db_session, 2302, user_id=user_id, balance=Decimal("0.00"))
    pot = _create_pot(test_app, user_id)

    allocate = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            source_account_id=source.id,
            amount="40.00",
            idempotency_key="safety-alloc",
        ),
        user_id=user_id,
    )
    assert allocate.status_code == 200

    duplicate = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            source_account_id=source.id,
            amount="40.00",
            idempotency_key="safety-alloc",
        ),
        user_id=user_id,
    )
    _assert_public_error(duplicate, 409)

    invalid_amount = post_aipa_dispatch(
        test_app,
        WalletAction.WITHDRAW,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            destination_account_id=destination.id,
            amount="0.00",
            idempotency_key="zero-withdraw",
        ),
        user_id=user_id,
    )
    _assert_public_error(invalid_amount, 400)

    test_db_session.refresh(source)
    test_db_session.refresh(destination)
    assert source.balance == Decimal("60.00")
    assert destination.balance == Decimal("0.00")
    assert test_db_session.get(Account, pot["id"]).balance == Decimal("40.00")
    assert test_db_session.query(LedgerEntry).count() == 1

    withdraw = post_aipa_dispatch(
        test_app,
        WalletAction.WITHDRAW,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            destination_account_id=destination.id,
            amount="40.00",
            idempotency_key="safety-withdraw",
        ),
        user_id=user_id,
    )
    assert withdraw.status_code == 200

    close = post_aipa_dispatch(
        test_app,
        WalletAction.CLOSE_POT,
        guarded_payload(user_id, pot_id=pot["id"]),
        user_id=user_id,
    )
    assert close.status_code == 200

    closed_pot_allocate = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        guarded_payload(
            user_id,
            pot_id=pot["id"],
            source_account_id=source.id,
            amount="1.00",
            idempotency_key="closed-pot-alloc",
        ),
        user_id=user_id,
    )
    _assert_public_error(closed_pot_allocate, 400)

    new_pot = _create_pot(test_app, user_id, name="Open Pot")
    source.closed_at = datetime(2026, 1, 3, 0, 0, 0)
    test_db_session.flush()

    closed_account_allocate = post_aipa_dispatch(
        test_app,
        WalletAction.ALLOCATE,
        guarded_payload(
            user_id,
            pot_id=new_pot["id"],
            source_account_id=source.id,
            amount="1.00",
            idempotency_key="closed-account-alloc",
        ),
        user_id=user_id,
    )
    _assert_public_error(closed_account_allocate, 400)

    reconcile = post_aipa_dispatch(
        test_app,
        WalletAction.RECONCILE,
        guarded_payload(user_id),
        user_id=user_id,
    )
    assert reconcile.status_code == 200
    assert reconcile.json()["result"]["status"] == "ok"


def test_safety_direct_pot_api_uses_409_for_duplicate_idempotency(
    test_app: TestClient,
    test_db_session: Session,
) -> None:
    user_id = 24
    source = seed_balance_account(test_db_session, 2401, user_id=user_id, balance=Decimal("100.00"))

    create = test_app.post(
        "/pots",
        json={"user_id": user_id, "currency": "INR", "name": "Direct Pot"},
    )
    assert create.status_code == 200
    pot = create.json()

    first = test_app.post(
        f"/pots/{pot['id']}/allocate",
        json={"source_account_id": source.id, "amount": "5.00", "idempotency_key": "direct-dup"},
    )
    assert first.status_code == 200

    duplicate = test_app.post(
        f"/pots/{pot['id']}/allocate",
        json={"source_account_id": source.id, "amount": "5.00", "idempotency_key": "direct-dup"},
    )
    _assert_public_error(duplicate, 409)
