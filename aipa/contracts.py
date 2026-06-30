"""
AIPA contract models for IB Wallet.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WalletAction(str, Enum):
    CREATE_POT = "CREATE_POT"
    LIST_POTS = "LIST_POTS"
    ALLOCATE = "ALLOCATE"
    WITHDRAW = "WITHDRAW"
    MOVE = "MOVE"
    CLOSE_POT = "CLOSE_POT"
    RECONCILE = "RECONCILE"


class AIPADispatch(BaseModel):
    trace_id: str = Field(..., min_length=1)
    user_id: int = Field(..., gt=0)
    action: WalletAction
    payload: dict[str, Any]


class AIPAResponse(BaseModel):
    trace_id: str
    status: str
    result: Any | None = None
    error: str | None = None
