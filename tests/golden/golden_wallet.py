"""Golden wallet scenario runner for IB Wallet.

This module executes deterministic golden scenarios against the existing
wallet services, AIPA dispatch router, and vault validation helpers.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aipa.gate import FastGateError, validate_dispatch
from aipa.router import dispatch_to_wallet
from models.account import Account
from models.ledger_entry import LedgerEntry
from services.reconcile import reconcile_user_accounts
from vault.consent import ConsentScope, TokenNotFoundError, validate_token
from vault.region import Region, RegionValidationError, pin_region, validate_user_region

from tests.golden.testdata import (
    AccountSnapshot,
    DispatchAction,
    GoldenScenario,
    LedgerEntrySnapshot,
    ReconcileAction,
    ScenarioExpectation,
    ValidateRegionAction,
    ValidateTokenAction,
)


def _create_account_from_snapshot(db: Session, snapshot: AccountSnapshot) -> Account:
    account = Account(
        id=snapshot.id,
        user_id=snapshot.user_id,
        account_type=snapshot.account_type,
        currency=snapshot.currency,
        name=snapshot.name,
        balance=snapshot.balance,
        target_amount=snapshot.target_amount,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=snapshot.closed_at,
    )
    db.add(account)
    return account


def _create_ledger_entry_from_snapshot(db: Session, snapshot: LedgerEntrySnapshot) -> LedgerEntry:
    entry = LedgerEntry(
        debit_account_id=snapshot.debit_account_id,
        credit_account_id=snapshot.credit_account_id,
        amount=snapshot.amount,
        currency=snapshot.currency,
        idempotency_key=snapshot.idempotency_key,
        created_at=snapshot.created_at or datetime(2026, 1, 1, 0, 0, 0),
    )
    db.add(entry)
    return entry


def _load_initial_state(db: Session, scenario: GoldenScenario) -> None:
    for snapshot in scenario.initial_accounts:
        _create_account_from_snapshot(db, snapshot)
    for snapshot in scenario.initial_ledger_entries:
        _create_ledger_entry_from_snapshot(db, snapshot)
    db.flush()


def _assert_account_snapshot(account: Account, snapshot: AccountSnapshot) -> None:
    assert account.id == snapshot.id
    assert account.user_id == snapshot.user_id
    assert account.account_type == snapshot.account_type
    assert account.currency == snapshot.currency
    assert account.name == snapshot.name
    assert account.balance == snapshot.balance
    assert account.target_amount == snapshot.target_amount
    if snapshot.expect_closed is True:
        assert account.closed_at is not None
    if snapshot.expect_closed is False:
        assert account.closed_at is None
    if snapshot.closed_at is not None:
        assert account.closed_at == snapshot.closed_at


def _compare_account_states(db: Session, snapshots: tuple[AccountSnapshot, ...]) -> None:
    for snapshot in snapshots:
        account = db.get(Account, snapshot.id)
        assert account is not None, f"Expected account {snapshot.id} to exist"
        _assert_account_snapshot(account, snapshot)


def _compare_list_accounts(actual_accounts: list[Account], expected_snapshots: tuple[AccountSnapshot, ...]) -> None:
    assert len(actual_accounts) == len(expected_snapshots)
    sorted_actual = sorted(actual_accounts, key=lambda account: account.id)
    sorted_expected = sorted(expected_snapshots, key=lambda snapshot: snapshot.id)
    for actual, expected in zip(sorted_actual, sorted_expected):
        _assert_account_snapshot(actual, expected)


def _execute_dispatch_action(db: Session, action: DispatchAction) -> Any:
    payload = {
        "trace_id": action.trace_id,
        "user_id": action.user_id,
        "action": action.action,
        "payload": action.payload,
    }
    validated = validate_dispatch(payload)
    response = dispatch_to_wallet(db=db, dispatch=validated)
    return response


def _execute_validate_token_action(action: ValidateTokenAction) -> Any:
    return validate_token(action.token_id, action.required_scope)


def _execute_validate_region_action(action: ValidateRegionAction) -> None:
    pin_region(user_id=action.user_id, region=action.pinned_region.value)
    validate_user_region(user_id=action.user_id, required_region=action.required_region)


def _execute_reconcile_action(action: ReconcileAction, db: Session) -> Any:
    return reconcile_user_accounts(db=db, user_id=action.user_id)


def _assert_expected_result(response: Any, expectation: ScenarioExpectation) -> None:
    if expectation.expected_list_accounts:
        assert isinstance(response.result, list)
        _compare_list_accounts(response.result, expectation.expected_list_accounts)

    if expectation.expected_reconcile_result is not None:
        if isinstance(response, dict):
            assert response == expectation.expected_reconcile_result
        else:
            assert response.result == expectation.expected_reconcile_result


def _response_status(response: Any) -> str | None:
    if isinstance(response, dict):
        return response.get("status")
    if hasattr(response, "status"):
        return response.status
    return None


def _response_error(response: Any) -> str | None:
    if isinstance(response, dict):
        return response.get("error")
    if hasattr(response, "error"):
        return response.error
    return None


def run_golden_scenario(db: Session, scenario: GoldenScenario) -> None:
    """Load initial state, execute the golden scenario, and assert expected results."""
    _load_initial_state(db, scenario)

    error = None
    response = None

    try:
        if isinstance(scenario.action, DispatchAction):
            response = _execute_dispatch_action(db, scenario.action)
        elif isinstance(scenario.action, ValidateTokenAction):
            _execute_validate_token_action(scenario.action)
        elif isinstance(scenario.action, ValidateRegionAction):
            _execute_validate_region_action(scenario.action)
        elif isinstance(scenario.action, ReconcileAction):
            response = _execute_reconcile_action(scenario.action, db)
        else:
            raise ValueError(f"Unsupported action type: {type(scenario.action)}")
    except BaseException as exc:
        error = exc

    if scenario.expectation.expected_error_type is not None:
        assert error is not None or _response_status(response) == "error", (
            f"Scenario '{scenario.name}' expected an error but none occurred"
        )
        if error is not None:
            assert isinstance(error, scenario.expectation.expected_error_type), (
                f"Scenario '{scenario.name}' expected {scenario.expectation.expected_error_type}, "
                f"received {type(error)}"
            )
            if scenario.expectation.expected_error_message_contains:
                assert scenario.expectation.expected_error_message_contains in str(error)
        else:
            assert _response_status(response) == "error"
            if scenario.expectation.expected_error_message_contains:
                response_error = _response_error(response)
                assert response_error is not None
                assert scenario.expectation.expected_error_message_contains in response_error
    else:
        assert error is None, f"Scenario '{scenario.name}' raised unexpected error: {error}"
        assert response is not None
        assert _response_status(response) == scenario.expectation.expected_status
        _assert_expected_result(response, scenario.expectation)

    if scenario.expectation.expected_account_states:
        _compare_account_states(db, scenario.expectation.expected_account_states)

    if scenario.expectation.expected_reconcile_result is not None and response is not None:
        if isinstance(response, dict):
            assert response == scenario.expectation.expected_reconcile_result
        else:
            assert response == scenario.expectation.expected_reconcile_result or (
                hasattr(response, "result") and response.result == scenario.expectation.expected_reconcile_result
            )
