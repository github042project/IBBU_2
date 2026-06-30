"""
API routes for IB Wallet AIPA dispatch.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from aipa.contracts import AIPAResponse, AIPADispatch
from aipa.gate import FastGateError, validate_dispatch
from aipa.router import dispatch_to_wallet
from db.session import get_db
from models.account import Account
from vault.consent import (
    ConsentScope,
    TokenExpiredError,
    TokenNotFoundError,
    validate_token,
)
from vault.region import RegionValidationError, pin_region

router = APIRouter(prefix="/aipa", tags=["aipa"])


class AIPADispatchRequest(BaseModel):
    trace_id: str
    user_id: int
    action: str
    payload: dict


def _serialize_result(result):
    if isinstance(result, Account):
        return {
            "id": result.id,
            "user_id": result.user_id,
            "account_type": result.account_type.value,
            "currency": result.currency,
            "name": result.name,
            "balance": result.balance,
            "target_amount": result.target_amount,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "closed_at": result.closed_at.isoformat() if result.closed_at else None,
        }
    if isinstance(result, list):
        return [_serialize_result(item) for item in result]
    return result


def _validate_vault_and_region(dispatch: AIPADispatch) -> None:
    token_id = dispatch.payload.get("token_id")
    if token_id is not None:
        token = validate_token(UUID(str(token_id)), ConsentScope.WALLET_WRITE)
        if token.user_id != dispatch.user_id:
            raise TokenNotFoundError("Token does not belong to dispatch user.")

    region = dispatch.payload.get("region")
    if region is not None:
        pin_region(user_id=dispatch.user_id, region=str(region))


def _status_for_wallet_error(dispatch: AIPADispatch, error: str | None) -> int:
    if dispatch.action.value == "RECONCILE":
        return 409

    message = (error or "").lower()
    if "already exists" in message or "duplicate" in message:
        return 409
    if "not found" in message or "does not exist" in message:
        return 404
    return 400


@router.post("/dispatch", response_model=AIPAResponse)
def dispatch(request: AIPADispatchRequest, db: Session = Depends(get_db)) -> AIPAResponse:
    try:
        validated = validate_dispatch(request.model_dump())
        _validate_vault_and_region(validated)
        response = dispatch_to_wallet(db=db, dispatch=validated)
        if response.status == "error":
            raise HTTPException(
                status_code=_status_for_wallet_error(validated, response.error),
                detail=response.error or "Wallet dispatch failed.",
            )
        response.result = _serialize_result(response.result)
    except FastGateError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (TokenNotFoundError, TokenExpiredError, ValueError) as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except RegionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Wallet dispatch failed.")

    return response
