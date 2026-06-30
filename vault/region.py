"""
Vault region pinning for IB Wallet.

Provides region selection, validation, and audit logging.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional


class Region(str, Enum):
    """Supported regions for IB Wallet."""
    INDIA = "INDIA"
    SWITZERLAND = "SWITZERLAND"


class RegionValidationError(Exception):
    """Raised when an unsupported region is provided."""


@dataclass
class RegionAuditRecord:
    user_id: int
    region: Region
    timestamp: datetime


_REGION_STORE: Dict[int, Region] = {}
_REGION_AUDIT_LOG: Dict[int, list[RegionAuditRecord]] = {}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def pin_region(user_id: int, region: str) -> Region:
    """Pin the selected region for a given user."""
    try:
        selected_region = Region(region)
    except ValueError as exc:
        raise RegionValidationError(f"Unsupported region: {region}") from exc

    _REGION_STORE[user_id] = selected_region
    _REGION_AUDIT_LOG.setdefault(user_id, []).append(
        RegionAuditRecord(user_id=user_id, region=selected_region, timestamp=_now_utc())
    )
    return selected_region


def get_region(user_id: int) -> Region:
    """Get the pinned region for a user, defaulting to INDIA."""
    return _REGION_STORE.get(user_id, Region.INDIA)


def validate_user_region(user_id: int, required_region: Region) -> None:
    """Validate that the user is pinned to the required region."""
    pinned = get_region(user_id)
    if pinned != required_region:
        raise RegionValidationError(
            f"User {user_id} is pinned to {pinned.value}, expected {required_region.value}."
        )
