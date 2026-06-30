import uuid

import pytest

from aipa.gate import FastGateError, validate_dispatch
from aipa.contracts import WalletAction


def make_payload(action: WalletAction) -> dict:
    base = {
        "trace_id": str(uuid.uuid4()),
        "user_id": 1,
        "action": action.value,
        "payload": {},
    }
    if action == WalletAction.CREATE_POT:
        base["payload"] = {"currency": "INR", "name": "My Pot"}
    elif action == WalletAction.ALLOCATE:
        base["payload"] = {"source_account_id": 1, "amount": "10.00", "idempotency_key": "key-1", "pot_id": 2}
    elif action == WalletAction.WITHDRAW:
        base["payload"] = {"destination_account_id": 2, "amount": "5.00", "idempotency_key": "key-2", "pot_id": 1}
    elif action == WalletAction.MOVE:
        base["payload"] = {"destination_pot_id": 3, "amount": "5.00", "idempotency_key": "key-3", "pot_id": 1}
    elif action == WalletAction.CLOSE_POT:
        base["payload"] = {"pot_id": 1}
    elif action == WalletAction.RECONCILE:
        base["payload"] = {}
    return base


def test_validate_dispatch_valid_payload() -> None:
    payload = make_payload(WalletAction.CREATE_POT)
    validated = validate_dispatch(payload)

    assert validated.trace_id == payload["trace_id"]
    assert validated.user_id == payload["user_id"]
    assert validated.action == WalletAction.CREATE_POT


def test_validate_dispatch_invalid_trace_id() -> None:
    payload = make_payload(WalletAction.LIST_POTS)
    payload["trace_id"] = "not-a-uuid"

    with pytest.raises(FastGateError):
        validate_dispatch(payload)


def test_validate_dispatch_invalid_user_id() -> None:
    payload = make_payload(WalletAction.LIST_POTS)
    payload["user_id"] = 0

    with pytest.raises(FastGateError):
        validate_dispatch(payload)


def test_validate_dispatch_invalid_action() -> None:
    payload = make_payload(WalletAction.LIST_POTS)
    payload["action"] = "FLY"

    with pytest.raises(FastGateError):
        validate_dispatch(payload)


def test_validate_dispatch_missing_payload() -> None:
    payload = make_payload(WalletAction.ALLOCATE)
    payload.pop("payload")

    with pytest.raises(FastGateError):
        validate_dispatch(payload)


def test_validate_dispatch_invalid_create_pot_payload() -> None:
    payload = make_payload(WalletAction.CREATE_POT)
    payload["payload"]["currency"] = "IN"

    with pytest.raises(FastGateError, match="currency must be a 3-character string"):
        validate_dispatch(payload)


def test_validate_dispatch_invalid_allocate_payload_fields() -> None:
    payload = make_payload(WalletAction.ALLOCATE)
    payload["payload"]["source_account_id"] = -1

    with pytest.raises(FastGateError, match="source_account_id must be a positive integer"):
        validate_dispatch(payload)
