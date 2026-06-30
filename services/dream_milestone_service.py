"""
Services for IB Dream — milestone engine.

Turns a Dream (a money goal) into a visual, milestone-based build. Every number here
is deterministic arithmetic — NOT AI — exactly as specified in the IB Dream roadmap
(Logic, Porsche and Milestone Builder sheets). The four rules:

  1. Step count   : by target size  -> <25k=6, 25k-2L=8, 2L-10L=10, >10L=12
  2. Milestone amt: target / steps
  3. Opacity      : 0.10 + (progress * 0.90)   (dream starts ghosted, becomes solid)
  4. Pace (ETA)   : gap to next step / monthly saving

This service only computes and describes. It never moves money. Deposits go through
the ledger (Day 2). The visual reads these numbers (Day 3).
"""

from decimal import Decimal, ROUND_UP
from typing import List, Dict, Optional

#from models.dream import Dream
class Dream:
    """
    Temporary Dream object for Day 1 verification.
    Will be replaced by the SQLAlchemy model in Day 2.
    """

    def __init__(
        self,
        name,
        target_amount,
        current_saved_amount=0,
        monthly_contribution=0,
    ):
        self.name = name
        self.target_amount = target_amount
        self.current_saved_amount = current_saved_amount
        self.monthly_contribution = monthly_contribution


# ── Rule 1: step count by aspirational size ──────────────────────────────────

# Thresholds straight from the roadmap Logic sheet.
def step_count_for(target_amount: Decimal) -> int:
    t = Decimal(str(target_amount))
    if t < Decimal("25000"):
        return 6
    if t <= Decimal("200000"):
        return 8
    if t <= Decimal("1000000"):
        return 10
    return 12


# ── Rule 2: milestone amount ─────────────────────────────────────────────────

def milestone_amount(target_amount: Decimal, steps: int) -> Decimal:
    return (Decimal(str(target_amount)) / Decimal(steps)).quantize(Decimal("0.01"))


# ── Rule 3: opacity (the "becomes real" feeling) ─────────────────────────────

def opacity_for(progress: Decimal) -> Decimal:
    """progress is 0..1. Dream starts at 10% visible, ends fully solid at 100%."""
    p = Decimal(str(progress))
    return (Decimal("0.10") + p * Decimal("0.90")).quantize(Decimal("0.001"))


# ── Build the full milestone ladder for a dream ──────────────────────────────

def build_milestones(dream: Dream) -> List[Dict]:
    """
    Return the ordered list of milestones for a dream, each with its rupee gate,
    target progress, opacity, the unlock state given current savings, and copy.
    """
    target = Decimal(str(dream.target_amount))
    saved = Decimal(str(dream.current_saved_amount or 0))
    steps = step_count_for(target)
    amt = milestone_amount(target, steps)

    out: List[Dict] = []
    for i in range(1, steps + 1):
        step_target = (amt * i).quantize(Decimal("0.01"))
        progress = (Decimal(i) / Decimal(steps))
        unlocked = saved >= step_target
        out.append({
            "step": i,
            "of": steps,
            "target_saved": str(step_target),
            "target_progress": float(progress.quantize(Decimal("0.0001"))),
            "opacity": float(opacity_for(progress)),
            "state": "unlocked" if unlocked else "locked",
            "copy": f"Step {i} of {steps} makes the dream more real",
        })
    return out


# ── Current state of the dream (what the visual reads) ───────────────────────

def dream_state(dream: Dream) -> Dict:
    target = Decimal(str(dream.target_amount))
    saved = Decimal(str(dream.current_saved_amount or 0))
    steps = step_count_for(target)
    amt = milestone_amount(target, steps)

    progress = (saved / target) if target > 0 else Decimal("0")
    progress = min(progress, Decimal("1"))
    current_opacity = opacity_for(progress)

    # how many steps are unlocked, and what the next gate is
    milestones = build_milestones(dream)
    unlocked = [m for m in milestones if m["state"] == "unlocked"]
    current_step = len(unlocked)
    next_m = milestones[current_step] if current_step < steps else None
    gap_to_next = (Decimal(next_m["target_saved"]) - saved) if next_m else Decimal("0")

    return {
        "dream": dream.name,
        "target_amount": str(target),
        "current_saved": str(saved),
        "steps": steps,
        "milestone_amount": str(amt),
        "progress_pct": float((progress * 100).quantize(Decimal("0.1"))),
        "visible_pct": float((current_opacity * 100).quantize(Decimal("0.1"))),
        "current_step": current_step,
        "next_step": next_m["step"] if next_m else None,
        "gap_to_next": str(gap_to_next.quantize(Decimal("0.01"))),
        "is_complete": current_step == steps,
    }


# ── Rule 4: pace / ETA (deterministic) ───────────────────────────────────────

def pace(dream: Dream) -> Dict:
    """
    Months to the next unlock and to the full dream, at the current monthly saving.
    Honest arithmetic: gap / monthly. Labelled deterministic, not AI.
    """
    target = Decimal(str(dream.target_amount))
    saved = Decimal(str(dream.current_saved_amount or 0))
    monthly = Decimal(str(dream.monthly_contribution or 0))

    state = dream_state(dream)
    gap_next = Decimal(state["gap_to_next"])
    gap_full = max(Decimal("0"), target - saved)

    def months(gap: Decimal) -> Optional[int]:
        if monthly <= 0:
            return None
        return int((gap / monthly).to_integral_value(rounding=ROUND_UP))

    return {
        "monthly_saving": str(monthly),
        "months_to_next_unlock": months(gap_next),
        "months_to_full_dream": months(gap_full),
        "note": "deterministic (gap / monthly) — not a model",
    }
