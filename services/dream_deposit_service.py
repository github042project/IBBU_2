"""
Day 2 - Dream Deposit Service

Receives a deposit into a dream, updates the saved amount,
then reuses the Day 1 milestone engine to recompute progress.

No milestone calculations live here.
Everything is delegated to dream_milestone_service.
"""

from decimal import Decimal

from services.dream_milestone_service import dream_state, pace


class DreamDepositError(Exception):
    """Raised when a dream deposit is invalid."""


class DreamLike:
    """
    Temporary Dream object.

    Day 2 still has no Dream database model,
    so this matches what the milestone engine expects.
    """

    def __init__(
        self,
        name: str,
        target_amount,
        current_saved_amount,
        monthly_contribution,
    ):
        self.name = name
        self.target_amount = Decimal(str(target_amount))
        self.current_saved_amount = Decimal(str(current_saved_amount))
        self.monthly_contribution = Decimal(str(monthly_contribution))


def deposit(
    dream_name: str,
    target_amount,
    current_saved_amount,
    monthly_contribution,
    deposit_amount,
):
    """
    Add money into a dream and return the updated
    milestone state + pace.

    No business logic is duplicated here.
    """

    deposit_amount = Decimal(str(deposit_amount))

    if deposit_amount <= Decimal("0"):
        raise DreamDepositError(
            "Deposit amount must be greater than zero."
        )

    new_saved = Decimal(str(current_saved_amount)) + deposit_amount

    dream = DreamLike(
        name=dream_name,
        target_amount=target_amount,
        current_saved_amount=new_saved,
        monthly_contribution=monthly_contribution,
    )

    return {
        "deposit": str(deposit_amount),
        "current_saved": str(new_saved),
        "state": dream_state(dream),
        "pace": pace(dream),
    }