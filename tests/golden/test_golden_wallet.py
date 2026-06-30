"""Golden wallet regression tests for IB Wallet."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from tests.golden.golden_wallet import run_golden_scenario
from tests.golden.testdata import GOLDEN_SCENARIOS


@pytest.mark.parametrize("scenario", GOLDEN_SCENARIOS, ids=[scenario.name for scenario in GOLDEN_SCENARIOS])
def test_golden_scenarios(test_db_session: Session, scenario) -> None:
    run_golden_scenario(test_db_session, scenario)
