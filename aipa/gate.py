"""
Fast gate validation for IB Wallet AIPA dispatch.

Implements pure request validation without database or network access.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from .contracts import AIPADispatch, WalletAction


class FastGateError(Exception):
    """Raised when a dispatch fails fast-gate validation."""


def _validate_trace_id(trace_id: str) -> None:
    if not trace_id or not isinstance(trace_id, str):
        raise FastGateError("trace_id must be a non-empty string")
    try:
        UUID(trace_id)
    except ValueError as exc:
        raise FastGateError("trace_id must be a valid UUID string") from exc


def _validate_user_id(user_id: int) -> None:
    if not isinstance(user_id, int) or user_id <= 0:
        raise FastGateError("user_id must be a positive integer")


def _validate_action(action: str) -> WalletAction:
    try:
        return WalletAction(action)
    except ValueError as exc:
        raise FastGateError(f"Unsupported action: {action}") from exc


def _validate_payload(action: WalletAction, payload: Any) -> None:
    if not isinstance(payload, dict):
        raise FastGateError("payload must be an object")

    required_fields: dict[WalletAction, list[str]] = {
        WalletAction.CREATE_POT: ["currency", "name"],
        WalletAction.LIST_POTS: [],
        WalletAction.ALLOCATE: ["pot_id", "source_account_id", "amount", "idempotency_key"],
        WalletAction.WITHDRAW: ["pot_id", "destination_account_id", "amount", "idempotency_key"],
        WalletAction.MOVE: ["pot_id", "destination_pot_id", "amount", "idempotency_key"],
        WalletAction.CLOSE_POT: ["pot_id"],
        WalletAction.RECONCILE: [],
    }

    for field_name in required_fields[action]:
        if field_name not in payload:
            raise FastGateError(f"Missing payload field: {field_name}")

    if action == WalletAction.CREATE_POT:
        if not isinstance(payload.get("currency"), str) or len(payload["currency"]) != 3:
            raise FastGateError("currency must be a 3-character string")
        if not isinstance(payload.get("name"), str) or not payload["name"].strip():
            raise FastGateError("name must be a non-empty string")

    if action in {WalletAction.ALLOCATE, WalletAction.WITHDRAW, WalletAction.MOVE}:
        if not isinstance(payload.get("amount"), (int, float, str)):
            raise FastGateError("amount must be a numeric value")
        if not payload.get("idempotency_key"):
            raise FastGateError("idempotency_key must be provided")

    if action == WalletAction.ALLOCATE:
        if not isinstance(payload.get("source_account_id"), int) or payload["source_account_id"] <= 0:
            raise FastGateError("source_account_id must be a positive integer")

    if action == WalletAction.WITHDRAW:
        if not isinstance(payload.get("destination_account_id"), int) or payload["destination_account_id"] <= 0:
            raise FastGateError("destination_account_id must be a positive integer")

    if action == WalletAction.MOVE:
        if not isinstance(payload.get("destination_pot_id"), int) or payload["destination_pot_id"] <= 0:
            raise FastGateError("destination_pot_id must be a positive integer")


def validate_dispatch(payload: dict[str, Any]) -> AIPADispatch:
    """Validate AIPA dispatch payload with pure in-memory rules."""
    try:
        dispatch = AIPADispatch(**payload)
    except ValidationError as exc:
        errors = exc.errors()
        if len(errors) == 1 and errors[0]["loc"] == ("action",) and errors[0]["type"] == "enum":
            raise FastGateError(f"Unsupported action: {payload.get('action')}") from exc
        raise FastGateError(str(exc)) from exc

    _validate_trace_id(dispatch.trace_id)
    _validate_user_id(dispatch.user_id)
    action = _validate_action(dispatch.action.value)
    _validate_payload(action, dispatch.payload)
    return dispatch
