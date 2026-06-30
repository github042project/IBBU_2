"""
Vault consent token handling for IB Wallet.

This module provides an in-memory consent token model and validation helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict
from uuid import UUID, uuid4


class ConsentScope(str, Enum):
    """Consent scopes available in IB Wallet."""
    WALLET_READ = "wallet:read"
    WALLET_WRITE = "wallet:write"


class TokenNotFoundError(Exception):
    """Raised when a consent token cannot be found."""


class TokenExpiredError(Exception):
    """Raised when a consent token is expired."""


@dataclass(frozen=True)
class VaultConsentToken:
    """Represents a vault consent token."""

    token_id: UUID
    user_id: int
    scope: ConsentScope
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.issued_at.tzinfo is None or self.issued_at.tzinfo.utcoffset(self.issued_at) is None:
            raise ValueError("issued_at must be timezone-aware UTC datetime")
        if self.expires_at.tzinfo is None or self.expires_at.tzinfo.utcoffset(self.expires_at) is None:
            raise ValueError("expires_at must be timezone-aware UTC datetime")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")

    def is_expired(self) -> bool:
        """Return True if the token is expired in UTC."""
        return datetime.now(timezone.utc) >= self.expires_at


_TOKEN_STORE: Dict[UUID, VaultConsentToken] = {}


def issue_token(user_id: int, scope: str, duration_seconds: int = 3600) -> VaultConsentToken:
    """Issue a new consent token for the given user and scope."""
    try:
        consent_scope = ConsentScope(scope)
    except ValueError as exc:
        raise ValueError(f"Unsupported consent scope: {scope}") from exc

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(seconds=duration_seconds)
    token = VaultConsentToken(
        token_id=uuid4(),
        user_id=user_id,
        scope=consent_scope,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    _TOKEN_STORE[token.token_id] = token
    return token


def validate_token(token_id: UUID, required_scope: ConsentScope) -> VaultConsentToken:
    """Validate an existing token and required scope."""
    token = _TOKEN_STORE.get(token_id)
    if token is None:
        raise TokenNotFoundError(f"Token {token_id} not found.")
    if token.scope != required_scope:
        raise ValueError(
            f"Token {token_id} does not grant required scope '{required_scope.value}'."
        )
    if token.is_expired():
        raise TokenExpiredError(f"Token {token_id} has expired.")
    return token


def require_consent_scope(required_scope: ConsentScope):
    """Decorator helper to validate a consent token passed as token_id."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            token_id = kwargs.get("token_id")
            if token_id is None:
                raise ValueError("Consent token_id is required.")
            if not isinstance(token_id, UUID):
                raise TypeError("token_id must be a UUID instance.")
            validate_token(token_id, required_scope)
            return func(*args, **kwargs)
        return wrapper
    return decorator
