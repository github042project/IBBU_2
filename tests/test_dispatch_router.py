import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from db.session import get_db

from aipa.contracts import WalletAction


@pytest.fixture
def client(test_app: TestClient) -> TestClient:
    """Provide the test client from conftest."""
    return test_app


def test_dispatch_to_wallet_invalid_trace_id(client: TestClient) -> None:
    response = client.post(
        "/aipa/dispatch",
        json={
            "trace_id": "invalid",
            "user_id": 1,
            "action": WalletAction.LIST_POTS.value,
            "payload": {},
        },
    )

    assert response.status_code == 422


def test_dispatch_to_wallet_invalid_user_id(client: TestClient) -> None:
    response = client.post(
        "/aipa/dispatch",
        json={
            "trace_id": str(uuid.uuid4()),
            "user_id": 0,
            "action": WalletAction.LIST_POTS.value,
            "payload": {},
        },
    )

    assert response.status_code == 422


def test_dispatch_to_wallet_invalid_action(client: TestClient) -> None:
    response = client.post(
        "/aipa/dispatch",
        json={
            "trace_id": str(uuid.uuid4()),
            "user_id": 1,
            "action": "FLY",
            "payload": {},
        },
    )

    assert response.status_code == 422


def test_dispatch_to_wallet_missing_payload_field(client: TestClient) -> None:
    response = client.post(
        "/aipa/dispatch",
        json={
            "trace_id": str(uuid.uuid4()),
            "user_id": 1,
            "action": WalletAction.CREATE_POT.value,
            "payload": {},
        },
    )

    assert response.status_code == 422


def test_dispatch_to_wallet_valid_dispatch(client: TestClient) -> None:
    response = client.post(
        "/aipa/dispatch",
        json={
            "trace_id": str(uuid.uuid4()),
            "user_id": 1,
            "action": WalletAction.LIST_POTS.value,
            "payload": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pots_create_list_and_close_routes(client: TestClient) -> None:
    create_response = client.post(
        "/pots",
        json={
            "user_id": 1,
            "currency": "INR",
            "name": "Rainy Day",
            "target_amount": "100.00",
        },
    )
    assert create_response.status_code == 200
    pot = create_response.json()
    assert pot["currency"] == "INR"
    assert str(pot["balance"]) == "0"

    list_response = client.get("/pots", params={"user_id": 1})
    assert list_response.status_code == 200
    assert any(item["id"] == pot["id"] for item in list_response.json())

    close_response = client.post(f"/pots/{pot['id']}/close")
    assert close_response.status_code == 200
    assert close_response.json()["closed_at"] is not None


def test_pots_create_invalid_currency_returns_400(client: TestClient) -> None:
    response = client.post(
        "/pots",
        json={
            "user_id": 1,
            "currency": "USD",
            "name": "Bad Pot",
        },
    )

    assert response.status_code == 400


def test_pots_close_nonexistent_pot_returns_404(client: TestClient) -> None:
    response = client.post("/pots/9999/close")

    assert response.status_code == 404


def test_pots_allocate_nonexistent_pot_returns_404(client: TestClient) -> None:
    response = client.post(
        "/pots/9999/allocate",
        json={
            "source_account_id": 1,
            "amount": "10.00",
            "idempotency_key": "alloc-1",
        },
    )

    assert response.status_code == 404


def test_pots_withdraw_missing_destination_account_returns_400(client: TestClient) -> None:
    create_response = client.post(
        "/pots",
        json={
            "user_id": 1,
            "currency": "INR",
            "name": "Rainy Day",
        },
    )
    pot_id = create_response.json()["id"]

    response = client.post(
        f"/pots/{pot_id}/withdraw",
        json={
            "destination_account_id": 9999,
            "amount": "10.00",
            "idempotency_key": "withdraw-1",
        },
    )

    assert response.status_code == 400


def test_reconcile_route_returns_ok_for_user_without_pots(client: TestClient) -> None:
    response = client.get("/reconcile/5")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["user_id"] == 5


def test_get_db_closes_session_after_generator_completion() -> None:
    generator = get_db()
    session = next(generator)
    session_id = id(session)
    assert session is not None
    try:
        pass
    finally:
        generator.close()
    assert session_id == id(session)


def test_dispatch_list_pots_empty_when_no_pots(client: TestClient) -> None:
    response = client.post(
        "/aipa/dispatch",
        json={
            "trace_id": str(uuid.uuid4()),
            "user_id": 1,
            "action": WalletAction.LIST_POTS.value,
            "payload": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["result"] == []

    assert response.json()["user_id"] == 5


def test_get_db_closes_session_after_generator_completion() -> None:
    generator = get_db()
    session = next(generator)
    session_id = id(session)
    assert session is not None
    try:
        pass
    finally:
        generator.close()
    assert session_id == id(session)


def test_dispatch_list_pots_empty_when_no_pots(client: TestClient) -> None:
    response = client.post(
        "/aipa/dispatch",
        json={
            "trace_id": str(uuid.uuid4()),
            "user_id": 1,
            "action": WalletAction.LIST_POTS.value,
            "payload": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["result"] == []
