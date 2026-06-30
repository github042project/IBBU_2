import uuid
from datetime import datetime, timedelta, timezone

import pytest

from vault.consent import (
    ConsentScope,
    TokenExpiredError,
    TokenNotFoundError,
    VaultConsentToken,
    issue_token,
    validate_token,
)


def test_issue_token_invalid_scope_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported consent scope"):
        issue_token(user_id=1, scope="wallet:delete", duration_seconds=60)


def test_require_consent_scope_decorator_rejects_missing_token() -> None:
    from vault.consent import require_consent_scope

    @require_consent_scope(ConsentScope.WALLET_READ)
    def protected_route(token_id=None):
        return True

    with pytest.raises(ValueError, match="Consent token_id is required"):
        protected_route()


def test_require_consent_scope_decorator_rejects_invalid_uuid() -> None:
    from uuid import UUID
    from vault.consent import require_consent_scope

    @require_consent_scope(ConsentScope.WALLET_READ)
    def protected_route(token_id=None):
        return True

    with pytest.raises(TypeError, match="token_id must be a UUID instance"):
        protected_route(token_id="not-a-uuid")


def test_issue_token_creates_valid_token() -> None:
    token = issue_token(user_id=1, scope=ConsentScope.WALLET_READ.value, duration_seconds=60)

    assert isinstance(token.token_id, uuid.UUID)
    assert token.user_id == 1
    assert token.scope == ConsentScope.WALLET_READ
    assert token.issued_at.tzinfo == timezone.utc
    assert token.expires_at.tzinfo == timezone.utc
    assert token.expires_at > token.issued_at
    assert not token.is_expired()


def test_validate_token_with_valid_token() -> None:
    token = issue_token(user_id=2, scope=ConsentScope.WALLET_WRITE.value, duration_seconds=60)
    validated = validate_token(token.token_id, ConsentScope.WALLET_WRITE)

    assert validated == token


def test_validate_token_raises_token_not_found() -> None:
    with pytest.raises(TokenNotFoundError):
        validate_token(uuid.uuid4(), ConsentScope.WALLET_READ)


def test_validate_token_raises_token_expired() -> None:
    issued_at = datetime.now(timezone.utc) - timedelta(seconds=60)
    expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    
    expired_token = VaultConsentToken(
        token_id=uuid.uuid4(),
        user_id=3,
        scope=ConsentScope.WALLET_READ,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    
    from vault.consent import _TOKEN_STORE
    _TOKEN_STORE[expired_token.token_id] = expired_token

    with pytest.raises(TokenExpiredError):
        validate_token(expired_token.token_id, ConsentScope.WALLET_READ)


def test_require_consent_scope_decorator_allows_valid_token() -> None:
    from vault.consent import require_consent_scope

    token = issue_token(user_id=9, scope=ConsentScope.WALLET_READ.value, duration_seconds=60)

    @require_consent_scope(ConsentScope.WALLET_READ)
    def protected_route(token_id=None):
        return True

    assert protected_route(token_id=token.token_id)
