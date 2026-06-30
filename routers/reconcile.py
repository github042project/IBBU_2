"""
API routes for IB Wallet reconciliation.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from services.reconcile import ReconciliationError, reconcile_user_accounts

router = APIRouter(prefix="/reconcile", tags=["reconcile"])


class ReconcileResponse(BaseModel):
    user_id: int
    open_pots: int
    closed_pots: int
    checked_pots: int
    status: str


@router.get("/{user_id}", response_model=ReconcileResponse)
def reconcile_user(user_id: int, db: Session = Depends(get_db)) -> ReconcileResponse:
    try:
        result = reconcile_user_accounts(db=db, user_id=user_id)
    except ReconciliationError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return ReconcileResponse(**result)
