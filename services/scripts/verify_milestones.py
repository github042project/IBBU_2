"""
Proof for IB Dream Day 1 — milestone engine.
Checks every number against the roadmap's own Porsche and Activa sheets.
Run:  python verify_milestones.py
"""
import sys
from decimal import Decimal
sys.path.insert(0, ".")
class DreamStatus:
    ACTIVE = "ACTIVE"


class Dream:
    def __init__(
        self,
        user_id,
        name,
        target_amount,
        current_saved_amount=0,
        monthly_contribution=0,
        dream_status=None,
    ):
        self.user_id = user_id
        self.name = name
        self.target_amount = target_amount
        self.current_saved_amount = current_saved_amount
        self.monthly_contribution = monthly_contribution
        self.dream_status = dream_status
from services.dream_milestone_service import (
    step_count_for, milestone_amount, opacity_for, build_milestones, dream_state, pace,
)

def mk(name, target, saved=0, monthly=0):
    return Dream(user_id=1, name=name, target_amount=Decimal(str(target)),
                 current_saved_amount=Decimal(str(saved)),
                 monthly_contribution=Decimal(str(monthly)),
                 dream_status=DreamStatus.ACTIVE)

print("="*64)
print("PROOF 1 — Step count rule (roadmap Logic sheet)")
print("="*64)
cases = [(14200,6,"Activa, <25k"),(80000,8,"laptop, 25k-2L"),(500000,10,"bike, 2L-10L"),(30000000,12,"Porsche, >10L")]
for target, expected, label in cases:
    got = step_count_for(Decimal(target))
    ok = "OK" if got==expected else "FAIL"
    print(f"  [{ok}] Rs {target:>10,} -> {got} steps  (expected {expected}) — {label}")
    assert got==expected

print("\n"+"="*64)
print("PROOF 2 — Porsche 3cr: 12 steps, every opacity matches the roadmap")
print("="*64)
# exact opacity column from the roadmap Porsche sheet
roadmap_porsche = [0.175,0.25,0.325,0.4,0.475,0.55,0.625,0.7,0.775,0.85,0.925,1.0]
porsche = mk("Porsche 911", 30000000)
ms = build_milestones(porsche)
assert len(ms)==12
print(f"  Steps: {len(ms)}  |  Milestone amount: Rs {milestone_amount(Decimal(30000000),12):,}")
print(f"  {'Step':>4} {'Target saved':>16} {'Opacity':>9} {'Roadmap':>9}")
for m, expected_op in zip(ms, roadmap_porsche):
    ok = "OK" if abs(m['opacity']-expected_op)<0.0005 else "FAIL"
    print(f"  {m['step']:>4} {int(float(m['target_saved'])):>16,} {m['opacity']:>9} {expected_op:>9}  [{ok}]")
    assert abs(m['opacity']-expected_op)<0.0005

print("\n"+"="*64)
print("PROOF 3 — Activa 14,200: 6 steps, opacities match the roadmap")
print("="*64)
roadmap_activa = [0.25,0.4,0.55,0.7,0.85,1.0]
activa = mk("Honda Activa 6G", 14200)
ms2 = build_milestones(activa)
assert len(ms2)==6
for m, expected_op in zip(ms2, roadmap_activa):
    ok = "OK" if abs(m['opacity']-expected_op)<0.0005 else "FAIL"
    print(f"  Step {m['step']}: target Rs {float(m['target_saved']):>9,.2f}  opacity {m['opacity']}  (roadmap {expected_op})  [{ok}]")
    assert abs(m['opacity']-expected_op)<0.0005

print("\n"+"="*64)
print("PROOF 4 — 'becomes real as you save' (opacity at a saved amount)")
print("="*64)
# roadmap: Porsche at 42% saved -> 47.8% visible
porsche_42 = mk("Porsche 911", 30000000, saved=Decimal("12600000"))  # 42% of 3cr
st = dream_state(porsche_42)
print(f"  Saved 42% of 3cr -> progress {st['progress_pct']}% , visible {st['visible_pct']}%  (roadmap: 47.8%)")
assert abs(st['visible_pct']-47.8)<0.05
print(f"  Current step: {st['current_step']} of {st['steps']} | next unlock at step {st['next_step']}, gap Rs {float(st['gap_to_next']):,.0f}")

print("\n"+"="*64)
print("PROOF 5 — Pace / ETA (deterministic)")
print("="*64)
# roadmap: at Rs 1,000 monthly, first layer (Rs 25L) takes 2,500 months
porsche_pace = mk("Porsche 911", 30000000, saved=0, monthly=1000)
pc = pace(porsche_pace)
print(f"  At Rs 1,000/month: next unlock in {pc['months_to_next_unlock']:,} months  (roadmap: 2,500)")
print(f"  Full dream in {pc['months_to_full_dream']:,} months")
print(f"  {pc['note']}")
assert pc['months_to_next_unlock']==2500

print("\n" + "="*64)
print("ALL PROOFS PASSED — milestone engine matches the roadmap exactly.")
print("="*64)
