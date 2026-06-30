from uuid import uuid4

from fastapi.testclient import TestClient

from aipa.contracts import WalletAction
from tests.integration.helpers import guarded_payload, post_aipa_dispatch
from vault.consent import ConsentScope, issue_token
from vault.region import Region, get_region


def test_aipa_flow_validates_fast_gate_vault_region_and_creates_pot(test_app: TestClient) -> None:
    response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        guarded_payload(2, currency="INR", name="AIPA Pot"),
        user_id=2,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["result"]["name"] == "AIPA Pot"
    assert get_region(2) == Region.INDIA


def test_aipa_flow_rejects_invalid_dispatch_before_wallet_services(test_app: TestClient) -> None:
    response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {"currency": "INR"},
        user_id=2,
    )

    assert response.status_code == 422
    assert "Missing payload field: name" in response.json()["detail"]


def test_aipa_flow_rejects_invalid_vault_token(test_app: TestClient) -> None:
    response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {
            "currency": "INR",
            "name": "Invalid Token",
            "token_id": str(uuid4()),
            "region": Region.INDIA.value,
        },
        user_id=2,
    )

    assert response.status_code == 403


def test_aipa_flow_rejects_invalid_region(test_app: TestClient) -> None:
    token = issue_token(user_id=3, scope=ConsentScope.WALLET_WRITE.value)
    response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {
            "currency": "INR",
            "name": "Bad Region",
            "token_id": str(token.token_id),
            "region": "BRAZIL",
        },
        user_id=3,
    )

    assert response.status_code == 400
