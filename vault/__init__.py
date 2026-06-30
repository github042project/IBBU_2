"""Vault package for IB Wallet.

Contains in-memory consent token and region pinning helpers.
"""

from .consent import (
    ConsentScope,
    TokenExpiredError,
    TokenNotFoundError,
    VaultConsentToken,
    issue_token,
    require_consent_scope,
    validate_token,
)
from .region import (
    Region,
    RegionValidationError,
    get_region,
    pin_region,
    validate_user_region,
)
