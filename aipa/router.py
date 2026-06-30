"""
AIPA dispatch router for IB Wallet.

Routes validated AIPA dispatch requests to existing wallet services.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from aipa.contracts import AIPAResponse, AIPADispatch, WalletAction
from aipa.gate import FastGateError
from db.session import get_db
from services.pot_service import (
    close_pot as close_pot_service,
    create_pot as create_pot_service,
    list_pots as list_pots_service,
    move_between_pots as move_between_pots_service,
    withdraw_from_pot as withdraw_from_pot_service,
    allocate_to_pot as allocate_to_pot_service,
)
from services.reconcile import reconcile_user_accounts

logger = logging.getLogger("aipa.dispatch")


def dispatch_to_wallet(db: Session, dispatch: AIPADispatch) -> AIPAResponse:
    start = perf_counter()
    status = "ok"
    result: Any | None = None
    error: str | None = None

    try:
        action = dispatch.action
        payload = dispatch.payload

        if action == WalletAction.CREATE_POT:
            result = create_pot_service(
                db=db,
                user_id=dispatch.user_id,
                currency=payload["currency"],
                name=payload["name"],
                target_amount=Decimal(str(payload.get("target_amount"))) if payload.get("target_amount") is not None else None,
            )
        elif action == WalletAction.LIST_POTS:
            result = list_pots_service(db=db, user_id=dispatch.user_id)
        elif action == WalletAction.ALLOCATE:
            result = allocate_to_pot_service(
                db=db,
                pot_id=int(payload["pot_id"]),
                source_account_id=int(payload["source_account_id"]),
                amount=Decimal(str(payload["amount"])),
                idempotency_key=str(payload["idempotency_key"]),
            )
        elif action == WalletAction.WITHDRAW:
            result = withdraw_from_pot_service(
                db=db,
                pot_id=int(payload["pot_id"]),
                destination_account_id=int(payload["destination_account_id"]),
                amount=Decimal(str(payload["amount"])),
                idempotency_key=str(payload["idempotency_key"]),
            )
        elif action == WalletAction.MOVE:
            result = move_between_pots_service(
                db=db,
                source_pot_id=int(payload["pot_id"]),
                destination_pot_id=int(payload["destination_pot_id"]),
                amount=Decimal(str(payload["amount"])),
                idempotency_key=str(payload["idempotency_key"]),
            )
        elif action == WalletAction.CLOSE_POT:
            result = close_pot_service(db=db, pot_id=int(payload["pot_id"]))
        elif action == WalletAction.RECONCILE:
            result = reconcile_user_accounts(db=db, user_id=dispatch.user_id)
        else:
            raise FastGateError(f"Unsupported action: {action}")
    except Exception as exc:
        status = "error"
        error = str(exc)
        logger.exception("AIPA dispatch failed", extra={
            "trace_id": dispatch.trace_id,
            "action": dispatch.action.value,
            "user_id": dispatch.user_id,
        })
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        logger.info(
            "AIPA dispatch completed",
            extra={
                "trace_id": dispatch.trace_id,
                "action": dispatch.action.value,
                "user_id": dispatch.user_id,
                "duration_ms": duration_ms,
                "status": status,
            },
        )

    return AIPAResponse(
        trace_id=dispatch.trace_id,
        status=status,
        result=result,
        error=error,
    )
