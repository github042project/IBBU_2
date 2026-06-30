"""
API routes for IB Wallet pots.
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from models.account import Account
from services.pot_service import (
    create_pot as create_pot_service,
    list_pots as list_pots_service,
    allocate_to_pot as allocate_to_pot_service,
    withdraw_from_pot as withdraw_from_pot_service,
    move_between_pots as move_between_pots_service,
    close_pot as close_pot_service,
    PotServiceError,
    PotNotFoundError,
    PotClosedError,
)

router = APIRouter(prefix="/pots", tags=["pots"])


class PotResponse(BaseModel):
    id: int
    user_id: int
    account_type: str
    currency: str
    name: str
    balance: Decimal
    target_amount: Optional[Decimal] = None
    created_at: Optional[str]
    closed_at: Optional[str]


class CreatePotRequest(BaseModel):
    user_id: int
    currency: str = Field(..., min_length=3, max_length=3)
    name: str
    target_amount: Optional[Decimal] = None


class AllocateRequest(BaseModel):
    source_account_id: int
    amount: Decimal
    idempotency_key: str


class WithdrawRequest(BaseModel):
    destination_account_id: int
    amount: Decimal
    idempotency_key: str


class MoveRequest(BaseModel):
    destination_pot_id: int
    amount: Decimal
    idempotency_key: str


def _to_response(account: Account) -> PotResponse:
    return PotResponse(
        id=account.id,
        user_id=account.user_id,
        account_type=account.account_type.value,
        currency=account.currency,
        name=account.name,
        balance=account.balance,
        target_amount=account.target_amount,
        created_at=account.created_at.isoformat() if account.created_at else None,
        closed_at=account.closed_at.isoformat() if account.closed_at else None,
    )


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PotNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, PotClosedError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, PotServiceError):
        if "already exists" in str(exc).lower():
            return HTTPException(status_code=409, detail=str(exc))
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.post("", response_model=PotResponse)
def create_pot(request: CreatePotRequest, db: Session = Depends(get_db)) -> PotResponse:
    try:
        pot = create_pot_service(
            db=db,
            user_id=request.user_id,
            currency=request.currency,
            name=request.name,
            target_amount=request.target_amount,
        )
    except PotServiceError as exc:
        raise _handle_service_error(exc)

    return _to_response(pot)


@router.get("", response_model=List[PotResponse])
def list_pots(user_id: int, db: Session = Depends(get_db)) -> List[PotResponse]:
    pots = list_pots_service(db=db, user_id=user_id)
    return [_to_response(pot) for pot in pots]


@router.post("/{pot_id}/allocate", response_model=PotResponse)
def allocate_to_pot(pot_id: int, request: AllocateRequest, db: Session = Depends(get_db)) -> PotResponse:
    try:
        pot = allocate_to_pot_service(
            db=db,
            pot_id=pot_id,
            source_account_id=request.source_account_id,
            amount=request.amount,
            idempotency_key=request.idempotency_key,
        )
    except PotServiceError as exc:
        raise _handle_service_error(exc)

    return _to_response(pot)


@router.post("/{pot_id}/withdraw", response_model=PotResponse)
def withdraw_from_pot(pot_id: int, request: WithdrawRequest, db: Session = Depends(get_db)) -> PotResponse:
    try:
        pot = withdraw_from_pot_service(
            db=db,
            pot_id=pot_id,
            destination_account_id=request.destination_account_id,
            amount=request.amount,
            idempotency_key=request.idempotency_key,
        )
    except PotServiceError as exc:
        raise _handle_service_error(exc)

    return _to_response(pot)


@router.post("/{pot_id}/move", response_model=PotResponse)
def move_between_pots(pot_id: int, request: MoveRequest, db: Session = Depends(get_db)) -> PotResponse:
    try:
        pot = move_between_pots_service(
            db=db,
            source_pot_id=pot_id,
            destination_pot_id=request.destination_pot_id,
            amount=request.amount,
            idempotency_key=request.idempotency_key,
        )
    except PotServiceError as exc:
        raise _handle_service_error(exc)

    return _to_response(pot)


@router.post("/{pot_id}/close", response_model=PotResponse)
def close_pot(pot_id: int, db: Session = Depends(get_db)) -> PotResponse:
    try:
        pot = close_pot_service(db=db, pot_id=pot_id)
    except PotServiceError as exc:
        raise _handle_service_error(exc)

    return _to_response(pot)
