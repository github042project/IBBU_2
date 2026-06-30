from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from aipa.contracts import WalletAction
from aipa.gate import validate_dispatch
from aipa.router import dispatch_to_wallet
from models.account import Account, AccountType
from vault.consent import ConsentScope, issue_token
from vault.region import Region


def seed_balance_account(
    db: Session,
    account_id: int,
    user_id: int = 1,
    balance: Decimal = Decimal("200.00"),
    currency: str = "INR",
    name: str = "Balance",
) -> Account:
    account = Account(
        id=account_id,
        user_id=user_id,
        account_type=AccountType.BALANCE,
        currency=currency,
        name=name,
        balance=balance,
        target_amount=None,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        closed_at=None,
    )
    db.add(account)
    db.flush()
    return account


def dispatch_service(
    db: Session,
    action: WalletAction,
    payload: dict,
    user_id: int = 1,
):
    dispatch = validate_dispatch(
        {
            "trace_id": str(uuid4()),
            "user_id": user_id,
            "action": action.value,
            "payload": payload,
        }
    )
    return dispatch_to_wallet(db=db, dispatch=dispatch)


def post_aipa_dispatch(
    client: TestClient,
    action: WalletAction | str,
    payload: dict,
    user_id: int = 1,
):
    action_value = action.value if isinstance(action, WalletAction) else action
    return client.post(
        "/aipa/dispatch",
        json={
            "trace_id": str(uuid4()),
            "user_id": user_id,
            "action": action_value,
            "payload": payload,
        },
    )


def guarded_payload(user_id: int, **payload: object) -> dict:
    token = issue_token(user_id=user_id, scope=ConsentScope.WALLET_WRITE.value)
    return {
        **payload,
        "token_id": str(token.token_id),
        "region": Region.INDIA.value,
    }
