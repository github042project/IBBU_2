"""
Services for IB Bud — Gen Z + AI demo features.

Three features, all built on the existing ledger. Nothing here invents a new way
to move money — every rupee still flows through services.ledger_service.post_entry,
so reconcile still holds and nothing can go missing.

  1. round_up_save        (Gen Z)  — round a spend up, save the spare change
  2. contribute_to_split  (Gen Z)  — many people fund one shared pot, fairly tracked
  3. can_i_afford         (AI)     — ask, get a plain-language verdict (no money moves)
"""

from decimal import Decimal, ROUND_UP
from typing import List, Dict
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.account import Account, AccountType
from models.ledger_entry import LedgerEntry
from services.ledger_service import post_entry
from services.pot_service import _get_pot


# ── 1. ROUND-UP SAVES ────────────────────────────────────────────────────────

def round_up_save(
    db: Session,
    user_balance_account_id: int,
    pot_id: int,
    spend_amount: Decimal,
    round_to: Decimal = Decimal("10"),
) -> Dict:
    """
    A user spends `spend_amount`. We round that up to the nearest `round_to`
    and move the spare change from their balance into the chosen pot.
    The spare change is one normal ledger entry — same engine as everything else.
    """
    rounded_total = (spend_amount / round_to).to_integral_value(rounding=ROUND_UP) * round_to
    spare = rounded_total - spend_amount

    if spare <= Decimal("0"):
        return {"spend": str(spend_amount), "spare_saved": "0.00", "note": "already a round number"}

    pot = _get_pot(db, pot_id)
    post_entry(
        db=db,
        debit_account_id=user_balance_account_id,
        credit_account_id=pot.id,
        amount=spare,
        currency=pot.currency,
        idempotency_key=f"roundup-{uuid4()}",
    )
    db.flush()
    return {
        "spend": str(spend_amount),
        "rounded_to": str(rounded_total),
        "spare_saved": str(spare),
        "pot_name": pot.name,
        "pot_balance": str(pot.balance),
    }


# ── 2. SPLIT-A-POT ───────────────────────────────────────────────────────────

def contribute_to_split(
    db: Session,
    contributor_balance_account_id: int,
    shared_pot_id: int,
    amount: Decimal,
) -> Dict:
    """
    One person chips into a SHARED pot. Unlike a personal pot, a split pot has
    many contributors, so we post straight through the ledger (the personal-pot
    owner check does not apply to a shared goal). The ledger records exactly who
    funded it, so 'who put what' is always provable.
    """
    pot = _get_pot(db, shared_pot_id)
    contributor = db.get(Account, contributor_balance_account_id)
    post_entry(
        db=db,
        debit_account_id=contributor.id,
        credit_account_id=pot.id,
        amount=amount,
        currency=pot.currency,
        idempotency_key=f"split-{uuid4()}",
    )
    db.flush()
    return {"contributor_account": contributor.id, "added": str(amount), "pot_balance": str(pot.balance)}


def split_breakdown(db: Session, shared_pot_id: int) -> List[Dict]:
    """Who put what into the shared pot — summed straight from the ledger."""
    rows = db.execute(
        select(LedgerEntry).where(LedgerEntry.credit_account_id == shared_pot_id)
    ).scalars().all()
    by_account: Dict[int, Decimal] = {}
    for e in rows:
        by_account[e.debit_account_id] = by_account.get(e.debit_account_id, Decimal("0")) + Decimal(str(e.amount))
    out = []
    for acc_id, total in by_account.items():
        acc = db.get(Account, acc_id)
        out.append({"account_id": acc_id, "owner_user_id": acc.user_id, "contributed": str(total)})
    return out


# ── 3. "CAN I AFFORD THIS?" (AI) ─────────────────────────────────────────────

def can_i_afford(
    db: Session,
    user_id: int,
    balance_account_id: int,
    purchase_amount: Decimal,
    goal_pot_id: int,
    monthly_saving: Decimal,
) -> Dict:
    """
    The AI gut-check. Reads the user's free balance and their goal, then returns a
    plain-language verdict. NO money moves here — AIPA only advises; the user decides.

    The 'delay' is deterministic math (how many extra weeks the goal slips if you
    spend now), framed as AIPA's answer. Honest: this is arithmetic, not a model.
    """
    balance = db.get(Account, balance_account_id)
    free = Decimal(str(balance.balance))
    goal = _get_pot(db, goal_pot_id)
    remaining_to_goal = max(Decimal("0"), Decimal(str(goal.target_amount or 0)) - Decimal(str(goal.balance)))

    if purchase_amount > free:
        verdict = "no"
        message = (f"Not right now — that's Rs {purchase_amount} but you only have "
                   f"Rs {free} free. Want me to suggest a smaller option?")
        weeks_delay = None
    else:
        weekly = (monthly_saving / Decimal("4")) if monthly_saving > 0 else Decimal("0")
        weeks_delay = int((purchase_amount / weekly).to_integral_value(rounding=ROUND_UP)) if weekly > 0 else None
        verdict = "yes_with_tradeoff"
        if weeks_delay:
            message = (f"Yes — but it pushes your {goal.name} goal back about "
                       f"{weeks_delay} weeks. Want me to rebalance so the goal stays on track?")
        else:
            message = f"Yes, you can afford it and your {goal.name} goal isn't affected."

    return {
        "question": f"Can I afford Rs {purchase_amount}?",
        "free_balance": str(free),
        "goal": goal.name,
        "remaining_to_goal": str(remaining_to_goal),
        "verdict": verdict,
        "aipa_says": message,
        "money_moved": False,
    }
