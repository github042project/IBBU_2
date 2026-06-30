"""Unit tests for AIPA dispatch routing and gateway validation."""

import pytest
from sqlalchemy.orm import Session

from aipa.contracts import WalletAction
from aipa.gate import FastGateError, validate_dispatch
from aipa.router import dispatch_to_wallet
from models.account import AccountType
from services.pot_service import create_pot


def test_fast_gate_rejects_invalid_trace_id() -> None:
    payload = {
        "trace_id": "not-a-uuid",
        "user_id": 1,
        "action": WalletAction.LIST_POTS.value,
        "payload": {},
    }

    with pytest.raises(FastGateError):
        validate_dispatch(payload)


def test_fast_gate_rejects_invalid_action() -> None:
    payload = {
        "trace_id": "11111111-1111-1111-1111-111111111111",
        "user_id": 1,
        "action": "FLY",
        "payload": {},
    }

    with pytest.raises(FastGateError):
        validate_dispatch(payload)


def test_dispatch_router_handles_create_pot(test_db_session: Session) -> None:
    request = {
        "trace_id": "22222222-2222-2222-2222-222222222222",
        "user_id": 100,
        "action": WalletAction.CREATE_POT.value,
        "payload": {"currency": "INR", "name": "Emergency Fund"},
    }

    validated = validate_dispatch(request)
    response = dispatch_to_wallet(db=test_db_session, dispatch=validated)

    assert response.status == "ok"
    assert response.result.user_id == 100
    assert response.result.account_type == AccountType.POT


def test_dispatch_router_handles_invalid_dispatch(test_db_session: Session) -> None:
    request = {
        "trace_id": "33333333-3333-3333-3333-333333333333",
        "user_id": 100,
        "action": "FLY",
        "payload": {},
    }

    with pytest.raises(FastGateError):
        validate_dispatch(request)


def test_dispatch_router_list_pots_returns_existing_pots(test_db_session: Session) -> None:
    create_pot(db=test_db_session, user_id=100, currency="INR", name="Target")

    request = {
        "trace_id": "44444444-4444-4444-4444-444444444444",
        "user_id": 100,
        "action": WalletAction.LIST_POTS.value,
        "payload": {},
    }

    validated = validate_dispatch(request)
    response = dispatch_to_wallet(db=test_db_session, dispatch=validated)

    assert response.status == "ok"
    assert isinstance(response.result, list)
    assert len(response.result) == 1
