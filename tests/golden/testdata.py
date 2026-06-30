"""Deterministic reference data for the IB Wallet golden test suite.

Each scenario includes a clear initial state, an action, and the expected
outcome. All values are deterministic and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from aipa.contracts import WalletAction
from vault.consent import ConsentScope
from vault.region import Region
from models.account import AccountType


@dataclass(frozen=True)
class AccountSnapshot:
    """Fixed account state used to seed and verify golden scenarios."""

    id: int
    user_id: int
    account_type: AccountType
    currency: str
    name: str
    balance: Decimal
    target_amount: Optional[Decimal] = None
    closed_at: Optional[datetime] = None
    expect_closed: Optional[bool] = None


@dataclass(frozen=True)
class LedgerEntrySnapshot:
    """Fixed ledger entry state used to seed golden scenarios."""

    debit_account_id: int
    credit_account_id: int
    amount: Decimal
    currency: str
    idempotency_key: str
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class DispatchAction:
    """A deterministic AIPA dispatch action payload."""

    trace_id: str
    user_id: int
    action: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class ValidateTokenAction:
    """A deterministic vault consent validation action."""

    token_id: UUID
    required_scope: ConsentScope


@dataclass(frozen=True)
class ValidateRegionAction:
    """A deterministic region validation action."""

    user_id: int
    pinned_region: Region
    required_region: Region


@dataclass(frozen=True)
class ReconcileAction:
    """A deterministic reconciliation action."""

    user_id: int


@dataclass(frozen=True)
class ScenarioExpectation:
    """Expected outcome for a golden scenario."""

    expected_status: str = "ok"
    expected_error_type: Optional[type[BaseException]] = None
    expected_error_message_contains: Optional[str] = None
    expected_account_states: Tuple[AccountSnapshot, ...] = ()
    expected_list_accounts: Tuple[AccountSnapshot, ...] = ()
    expected_reconcile_result: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class GoldenScenario:
    """A reference scenario for the IB Wallet golden set."""

    name: str
    description: str
    initial_accounts: Tuple[AccountSnapshot, ...]
    initial_ledger_entries: Tuple[LedgerEntrySnapshot, ...]
    action: Any
    expectation: ScenarioExpectation


# Standard timestamps used for deterministic closed-account state.
_FIXED_CLOSED_AT = datetime(2026, 1, 1, 12, 0, 0)


GOLDEN_SCENARIOS: Tuple[GoldenScenario, ...] = (
    GoldenScenario(
        name="create_pot",
        description=(
            "Create a new INR pot for an existing balance account. "
            "The new pot is created with a zero balance and a deterministically "
            "assigned target amount."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=1,
                user_id=100,
                account_type=AccountType.BALANCE,
                currency="INR",
                name="Main Balance",
                balance=Decimal("1000.00"),
            ),
        ),
        initial_ledger_entries=(),
        action=DispatchAction(
            trace_id="11111111-1111-1111-1111-111111111111",
            user_id=100,
            action=WalletAction.CREATE_POT.value,
            payload={
                "currency": "INR",
                "name": "Emergency Fund",
                "target_amount": "500.00",
            },
        ),
        expectation=ScenarioExpectation(
            expected_status="ok",
            expected_account_states=(
                AccountSnapshot(
                    id=1,
                    user_id=100,
                    account_type=AccountType.BALANCE,
                    currency="INR",
                    name="Main Balance",
                    balance=Decimal("1000.00"),
                    expect_closed=False,
                ),
                AccountSnapshot(
                    id=2,
                    user_id=100,
                    account_type=AccountType.POT,
                    currency="INR",
                    name="Emergency Fund",
                    balance=Decimal("0.00"),
                    target_amount=Decimal("500.00"),
                    expect_closed=False,
                ),
            ),
        ),
    ),
    GoldenScenario(
        name="list_pots",
        description=(
            "Verify that listing pots returns all pot accounts for the user, "
            "including open and closed pot accounts."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=1,
                user_id=100,
                account_type=AccountType.BALANCE,
                currency="INR",
                name="Main Balance",
                balance=Decimal("2500.00"),
            ),
            AccountSnapshot(
                id=2,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Rainy Day",
                balance=Decimal("100.00"),
                expect_closed=False,
            ),
            AccountSnapshot(
                id=3,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Vacation",
                balance=Decimal("0.00"),
                closed_at=_FIXED_CLOSED_AT,
                expect_closed=True,
            ),
        ),
        initial_ledger_entries=(),
        action=DispatchAction(
            trace_id="22222222-2222-2222-2222-222222222222",
            user_id=100,
            action=WalletAction.LIST_POTS.value,
            payload={},
        ),
        expectation=ScenarioExpectation(
            expected_status="ok",
            expected_list_accounts=(
                AccountSnapshot(
                    id=2,
                    user_id=100,
                    account_type=AccountType.POT,
                    currency="INR",
                    name="Rainy Day",
                    balance=Decimal("100.00"),
                    expect_closed=False,
                ),
                AccountSnapshot(
                    id=3,
                    user_id=100,
                    account_type=AccountType.POT,
                    currency="INR",
                    name="Vacation",
                    balance=Decimal("0.00"),
                    expect_closed=True,
                ),
            ),
        ),
    ),
    GoldenScenario(
        name="allocate_funds",
        description=(
            "Allocate funds from the user balance account into an open pot. "
            "The transaction is recorded with a deterministic idempotency key."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=1,
                user_id=100,
                account_type=AccountType.BALANCE,
                currency="INR",
                name="Main Balance",
                balance=Decimal("1000.00"),
                expect_closed=False,
            ),
            AccountSnapshot(
                id=2,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Rainy Day",
                balance=Decimal("0.00"),
                target_amount=Decimal("300.00"),
                expect_closed=False,
            ),
        ),
        initial_ledger_entries=(),
        action=DispatchAction(
            trace_id="33333333-3333-3333-3333-333333333333",
            user_id=100,
            action=WalletAction.ALLOCATE.value,
            payload={
                "pot_id": 2,
                "source_account_id": 1,
                "amount": "250.00",
                "idempotency_key": "alloc-001",
            },
        ),
        expectation=ScenarioExpectation(
            expected_status="ok",
            expected_account_states=(
                AccountSnapshot(
                    id=1,
                    user_id=100,
                    account_type=AccountType.BALANCE,
                    currency="INR",
                    name="Main Balance",
                    balance=Decimal("750.00"),
                    expect_closed=False,
                ),
                AccountSnapshot(
                    id=2,
                    user_id=100,
                    account_type=AccountType.POT,
                    currency="INR",
                    name="Rainy Day",
                    balance=Decimal("250.00"),
                    target_amount=Decimal("300.00"),
                    expect_closed=False,
                ),
            ),
        ),
    ),
    GoldenScenario(
        name="withdraw_funds",
        description=(
            "Withdraw funds from a pot back into the user balance account. "
            "The operation uses a deterministic idempotency key."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=1,
                user_id=100,
                account_type=AccountType.BALANCE,
                currency="INR",
                name="Main Balance",
                balance=Decimal("750.00"),
                expect_closed=False,
            ),
            AccountSnapshot(
                id=2,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Rainy Day",
                balance=Decimal("250.00"),
                expect_closed=False,
            ),
        ),
        initial_ledger_entries=(),
        action=DispatchAction(
            trace_id="44444444-4444-4444-4444-444444444444",
            user_id=100,
            action=WalletAction.WITHDRAW.value,
            payload={
                "pot_id": 2,
                "destination_account_id": 1,
                "amount": "100.00",
                "idempotency_key": "withdraw-001",
            },
        ),
        expectation=ScenarioExpectation(
            expected_status="ok",
            expected_account_states=(
                AccountSnapshot(
                    id=1,
                    user_id=100,
                    account_type=AccountType.BALANCE,
                    currency="INR",
                    name="Main Balance",
                    balance=Decimal("850.00"),
                    expect_closed=False,
                ),
                AccountSnapshot(
                    id=2,
                    user_id=100,
                    account_type=AccountType.POT,
                    currency="INR",
                    name="Rainy Day",
                    balance=Decimal("150.00"),
                    expect_closed=False,
                ),
            ),
        ),
    ),
    GoldenScenario(
        name="move_between_pots",
        description=(
            "Move funds from one open pot to another open pot for the same user. "
            "A deterministic idempotency key prevents duplicates."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=2,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Rainy Day",
                balance=Decimal("150.00"),
                expect_closed=False,
            ),
            AccountSnapshot(
                id=3,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Vacation",
                balance=Decimal("50.00"),
                expect_closed=False,
            ),
        ),
        initial_ledger_entries=(),
        action=DispatchAction(
            trace_id="55555555-5555-5555-5555-555555555555",
            user_id=100,
            action=WalletAction.MOVE.value,
            payload={
                "pot_id": 2,
                "destination_pot_id": 3,
                "amount": "100.00",
                "idempotency_key": "move-001",
            },
        ),
        expectation=ScenarioExpectation(
            expected_status="ok",
            expected_account_states=(
                AccountSnapshot(
                    id=2,
                    user_id=100,
                    account_type=AccountType.POT,
                    currency="INR",
                    name="Rainy Day",
                    balance=Decimal("50.00"),
                    expect_closed=False,
                ),
                AccountSnapshot(
                    id=3,
                    user_id=100,
                    account_type=AccountType.POT,
                    currency="INR",
                    name="Vacation",
                    balance=Decimal("150.00"),
                    expect_closed=False,
                ),
            ),
        ),
    ),
    GoldenScenario(
        name="close_empty_pot",
        description=(
            "Close an empty pot account and verify that the pot is marked as closed."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=4,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Emergency Fund",
                balance=Decimal("0.00"),
                expect_closed=False,
            ),
        ),
        initial_ledger_entries=(),
        action=DispatchAction(
            trace_id="66666666-6666-6666-6666-666666666666",
            user_id=100,
            action=WalletAction.CLOSE_POT.value,
            payload={"pot_id": 4},
        ),
        expectation=ScenarioExpectation(
            expected_status="ok",
            expected_account_states=(
                AccountSnapshot(
                    id=4,
                    user_id=100,
                    account_type=AccountType.POT,
                    currency="INR",
                    name="Emergency Fund",
                    balance=Decimal("0.00"),
                    expect_closed=True,
                ),
            ),
        ),
    ),
    GoldenScenario(
        name="reject_close_with_balance",
        description=(
            "Reject a close request for a pot that still has a positive balance."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=2,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Rainy Day",
                balance=Decimal("50.00"),
                expect_closed=False,
            ),
        ),
        initial_ledger_entries=(),
        action=DispatchAction(
            trace_id="77777777-7777-7777-7777-777777777777",
            user_id=100,
            action=WalletAction.CLOSE_POT.value,
            payload={"pot_id": 2},
        ),
        expectation=ScenarioExpectation(
            expected_status="error",
            expected_error_type=Exception,
            expected_error_message_contains="Pot must have a zero balance",
        ),
    ),
    GoldenScenario(
        name="duplicate_idempotency_key",
        description=(
            "Reject an allocation request when the idempotency key has already been used."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=1,
                user_id=100,
                account_type=AccountType.BALANCE,
                currency="INR",
                name="Main Balance",
                balance=Decimal("900.00"),
                expect_closed=False,
            ),
            AccountSnapshot(
                id=2,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Rainy Day",
                balance=Decimal("100.00"),
                expect_closed=False,
            ),
        ),
        initial_ledger_entries=(
            LedgerEntrySnapshot(
                debit_account_id=1,
                credit_account_id=2,
                amount=Decimal("100.00"),
                currency="INR",
                idempotency_key="dup-001",
            ),
        ),
        action=DispatchAction(
            trace_id="88888888-8888-8888-8888-888888888888",
            user_id=100,
            action=WalletAction.ALLOCATE.value,
            payload={
                "pot_id": 2,
                "source_account_id": 1,
                "amount": "100.00",
                "idempotency_key": "dup-001",
            },
        ),
        expectation=ScenarioExpectation(
            expected_status="error",
            expected_error_type=Exception,
            expected_error_message_contains="idempotency key 'dup-001' already exists",
        ),
    ),
    GoldenScenario(
        name="invalid_dispatch",
        description=(
            "Reject a dispatch payload with an unsupported wallet action."
        ),
        initial_accounts=(),
        initial_ledger_entries=(),
        action=DispatchAction(
            trace_id="99999999-9999-9999-9999-999999999999",
            user_id=100,
            action="FLY",
            payload={},
        ),
        expectation=ScenarioExpectation(
            expected_status="error",
            expected_error_type=Exception,
            expected_error_message_contains="Unsupported action",
        ),
    ),
    GoldenScenario(
        name="invalid_vault_token",
        description=(
            "Reject a vault consent token validation attempt for a token that does not exist."
        ),
        initial_accounts=(),
        initial_ledger_entries=(),
        action=ValidateTokenAction(
            token_id=UUID("00000000-0000-0000-0000-000000000000"),
            required_scope=ConsentScope.WALLET_WRITE,
        ),
        expectation=ScenarioExpectation(
            expected_status="error",
            expected_error_type=Exception,
            expected_error_message_contains="not found",
        ),
    ),
    GoldenScenario(
        name="invalid_region",
        description=(
            "Reject region validation for a user pinned to the wrong region."
        ),
        initial_accounts=(),
        initial_ledger_entries=(),
        action=ValidateRegionAction(
            user_id=600,
            pinned_region=Region.INDIA,
            required_region=Region.SWITZERLAND,
        ),
        expectation=ScenarioExpectation(
            expected_status="error",
            expected_error_type=Exception,
            expected_error_message_contains="expected SWITZERLAND",
        ),
    ),
    GoldenScenario(
        name="successful_reconciliation",
        description=(
            "Reconcile a user account when ledger entries and pot balances match exactly."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=1,
                user_id=100,
                account_type=AccountType.BALANCE,
                currency="INR",
                name="Main Balance",
                balance=Decimal("900.00"),
                expect_closed=False,
            ),
            AccountSnapshot(
                id=2,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Rainy Day",
                balance=Decimal("100.00"),
                expect_closed=False,
            ),
            AccountSnapshot(
                id=3,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Vacation",
                balance=Decimal("0.00"),
                closed_at=_FIXED_CLOSED_AT,
                expect_closed=True,
            ),
        ),
        initial_ledger_entries=(
            LedgerEntrySnapshot(
                debit_account_id=1,
                credit_account_id=2,
                amount=Decimal("100.00"),
                currency="INR",
                idempotency_key="reconcile-001",
            ),
        ),
        action=ReconcileAction(user_id=100),
        expectation=ScenarioExpectation(
            expected_status="ok",
            expected_reconcile_result={
                "user_id": 100,
                "open_pots": 1,
                "closed_pots": 1,
                "checked_pots": 2,
                "status": "ok",
            },
        ),
    ),
    GoldenScenario(
        name="failed_reconciliation_ledger_drift",
        description=(
            "Fail reconciliation when a pot balance does not match its ledger entries."
        ),
        initial_accounts=(
            AccountSnapshot(
                id=2,
                user_id=100,
                account_type=AccountType.POT,
                currency="INR",
                name="Rainy Day",
                balance=Decimal("120.00"),
                expect_closed=False,
            ),
        ),
        initial_ledger_entries=(
            LedgerEntrySnapshot(
                debit_account_id=1,
                credit_account_id=2,
                amount=Decimal("100.00"),
                currency="INR",
                idempotency_key="drift-001",
            ),
        ),
        action=ReconcileAction(user_id=100),
        expectation=ScenarioExpectation(
            expected_status="error",
            expected_error_type=Exception,
            expected_error_message_contains="Balance mismatch for pot",
        ),
    ),
)
