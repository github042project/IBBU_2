from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from aipa.contracts import WalletAction
from tests.integration.helpers import post_aipa_dispatch
from vault.consent import ConsentScope, VaultConsentToken, issue_token, validate_token
from vault.region import Region


def test_vault_flow_blocks_wallet_write_without_write_scope(test_app: TestClient) -> None:
    token = issue_token(user_id=4, scope=ConsentScope.WALLET_READ.value)
    response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {
            "currency": "INR",
            "name": "Read Only Token",
            "token_id": str(token.token_id),
            "region": Region.INDIA.value,
        },
        user_id=4,
    )

    assert response.status_code == 403


def test_vault_flow_rejects_expired_token_for_wallet_mutation(test_app: TestClient) -> None:
    expired_token = VaultConsentToken(
        token_id=uuid4(),
        user_id=5,
        scope=ConsentScope.WALLET_WRITE,
        issued_at=datetime.now(timezone.utc) - timedelta(seconds=120),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    from vault.consent import _TOKEN_STORE

    _TOKEN_STORE[expired_token.token_id] = expired_token

    response = post_aipa_dispatch(
        test_app,
        WalletAction.CREATE_POT,
        {
            "currency": "INR",
            "name": "Expired Token",
            "token_id": str(expired_token.token_id),
            "region": Region.INDIA.value,
        },
        user_id=5,
    )

    assert response.status_code == 403


def test_vault_flow_accepts_valid_write_token() -> None:
    token = issue_token(user_id=6, scope=ConsentScope.WALLET_WRITE.value)

    assert validate_token(token.token_id, ConsentScope.WALLET_WRITE) == token
