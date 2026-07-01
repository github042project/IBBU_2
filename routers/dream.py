"""
Router for IB Dream — Day 1 milestone engine demo.

A thin HTTP layer over the existing, already-verified
services/dream_milestone_service.py. This router contains NO business logic —
it only adapts request input into the shape the service expects and shapes the
result for the response. Every milestone calculation lives in the service.

Day 1 note: the Dream SQLAlchemy model is not built yet (Day 2). The service is
DB-independent and accepts any object matching its DreamLike protocol, so here we
pass a lightweight in-memory `_DreamLike` dataclass. No SQLAlchemy, no persistence.
When the real Dream model lands, it satisfies the same protocol and the service
and router need no change.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

# Reuse the existing milestone service — never duplicate its logic.
from services.dream_milestone_service import (
    step_count_for,
    milestone_amount,
    opacity_for,
    dream_state,
    pace,
)
from services.dream_deposit_service import (
    deposit,
    DreamDepositError,
)

router = APIRouter(
    prefix="/dream",
    tags=["IB Dream"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Temporary in-memory stand-in for the not-yet-built Dream model.
# Satisfies the service's DreamLike protocol by exposing the four read attributes.
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _DreamLike:
    name: str
    target_amount: Decimal
    current_saved_amount: Decimal
    monthly_contribution: Decimal


# ──────────────────────────────────────────────────────────────────────────────
# Request / response models (temporary — Day 1 demo only), Pydantic v2 style
# ──────────────────────────────────────────────────────────────────────────────

class DreamInput(BaseModel):
    dream_name: str = Field(..., description="A name for the dream.")
    target_amount: Decimal = Field(..., gt=0, description="Target amount in rupees.")
    current_saved_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Amount saved so far.")
    monthly_contribution: Decimal = Field(default=Decimal("0"), ge=0, description="Planned monthly saving.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "dream_name": "Porsche",
                    "target_amount": 30000000,
                    "current_saved_amount": 12600000,
                    "monthly_contribution": 1000,
                }
            ]
        }
    }

    def to_dreamlike(self) -> _DreamLike:
        """Adapt the request into the object the service reads. No logic here."""
        return _DreamLike(
            name=self.dream_name,
            target_amount=self.target_amount,
            current_saved_amount=self.current_saved_amount,
            monthly_contribution=self.monthly_contribution,
        )


class StepCountResponse(BaseModel):
    steps: int = Field(..., examples=[12])


class MilestoneAmountResponse(BaseModel):
    steps: int = Field(..., examples=[12])
    milestone_amount: str = Field(..., examples=["2500000.00"])


class OpacityResponse(BaseModel):
    opacity: float = Field(..., examples=[0.478])


class DreamStateResponse(BaseModel):
    dream: str
    target_amount: str
    current_saved: str
    steps: int
    milestone_amount: str
    progress_pct: float
    visible_pct: float
    current_step: int
    next_step: Optional[int]
    gap_to_next: str
    is_complete: bool


class PaceResponse(BaseModel):
    monthly_saving: str
    months_to_next_unlock: Optional[int]
    months_to_full_dream: Optional[int]
    note: str


class DemoResponse(BaseModel):
    dream: str
    steps: int
    milestone_amount: str
    progress_pct: float
    visible_pct: float
    current_step: int
    next_step: Optional[int]
    gap_to_next: str
    months_to_next_unlock: Optional[int]
    months_to_full_dream: Optional[int]


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints — each delegates straight to the existing service
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/step-count",
    response_model=StepCountResponse,
    summary="Step count for a dream",
    description=(
        "Returns how many milestone steps a dream is split into (6, 8, 10 or 12), "
        "based on its target amount. Deterministic rule from the roadmap Logic sheet: "
        "under ₹25k → 6, ₹25k–₹2L → 8, ₹2L–₹10L → 10, above ₹10L → 12."
    ),
)
def get_step_count(
    target_amount: Decimal = Query(..., gt=0, examples=[30000000], description="The dream's target amount in rupees."),
):
    return StepCountResponse(steps=step_count_for(target_amount))


@router.get(
    "/milestone-amount",
    response_model=MilestoneAmountResponse,
    summary="Milestone amount for a dream",
    description="Returns the rupee size of each milestone step (target ÷ steps), along with the step count.",
)
def get_milestone_amount(
    target_amount: Decimal = Query(..., gt=0, examples=[30000000], description="The dream's target amount in rupees."),
):
    steps = step_count_for(target_amount)
    return MilestoneAmountResponse(steps=steps, milestone_amount=str(milestone_amount(target_amount, steps)))


@router.get(
    "/opacity",
    response_model=OpacityResponse,
    summary="Dream visibility (opacity) at a given progress",
    description=(
        "Returns how 'solid' the dream looks at a given progress (0 to 1). "
        "Formula: 0.10 + progress × 0.90 — a ghosted dream becomes fully solid at 100%."
    ),
)
def get_opacity(
    progress: Decimal = Query(..., ge=0, le=1, examples=[0.42], description="Progress toward the goal, 0 to 1."),
):
    return OpacityResponse(opacity=float(opacity_for(progress)))


@router.post(
    "/state",
    response_model=DreamStateResponse,
    summary="Full current state of a dream",
    description=(
        "Given a dream's numbers, returns progress %, visible % (opacity), current step, "
        "next step, gap to the next unlock, milestone amount and step count. "
        "Calls the existing dream_state() service."
    ),
)
def post_dream_state(body: DreamInput):
    return DreamStateResponse(**dream_state(body.to_dreamlike()))


@router.post(
    "/pace",
    response_model=PaceResponse,
    summary="Pace / ETA for a dream",
    description=(
        "Returns months to the next unlock and months to the full dream at the current "
        "monthly saving. Deterministic (gap ÷ monthly). Calls the existing pace() service."
    ),
)
def post_pace(body: DreamInput):
    return PaceResponse(**pace(body.to_dreamlike()))


class DreamDepositRequest(DreamInput):
    deposit_amount: Decimal = Field(
        ...,
        gt=0,
        description="Amount to deposit into the dream."
    )


class DreamDepositResponse(BaseModel):
    deposit: str
    current_saved: str
    state: DreamStateResponse
    pace: PaceResponse


@router.post(
    "/demo",
    response_model=DemoResponse,
    summary="Everything together (live demo)",
    description=(
        "One call returning step count, milestone amount, progress, visibility, current/next "
        "step, gap and pace — the full Day 1 story in a single response. Used only for the live demo."
    ),
)
def post_demo(body: DreamInput):
    dream = body.to_dreamlike()
    state = dream_state(dream)
    pace_info = pace(dream)
    return DemoResponse(
        dream=state["dream"],
        steps=state["steps"],
        milestone_amount=state["milestone_amount"],
        progress_pct=state["progress_pct"],
        visible_pct=state["visible_pct"],
        current_step=state["current_step"],
        next_step=state["next_step"],
        gap_to_next=state["gap_to_next"],
        months_to_next_unlock=pace_info["months_to_next_unlock"],
        months_to_full_dream=pace_info["months_to_full_dream"],
    )
@router.post(
    "/deposit",
    response_model=DreamDepositResponse,
    summary="Deposit money into a dream",
    description=(
        "Adds money to the dream, updates the saved amount, "
        "and recomputes milestones using the existing milestone engine."
    ),
)
def deposit_into_dream(body: DreamDepositRequest):
    try:
        result = deposit(
            dream_name=body.dream_name,
            target_amount=body.target_amount,
            current_saved_amount=body.current_saved_amount,
            monthly_contribution=body.monthly_contribution,
            deposit_amount=body.deposit_amount,
        )

        return DreamDepositResponse(
            deposit=result["deposit"],
            current_saved=result["current_saved"],
            state=DreamStateResponse(**result["state"]),
            pace=PaceResponse(**result["pace"]),
        )

    except DreamDepositError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
