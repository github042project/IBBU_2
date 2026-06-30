"""
IB Bud — live feature demo. Runs real operations through the real ledger and
prints exactly what happens. Nothing is faked: every rupee moves via post_entry,
and we reconcile at the end to prove nothing was lost.

Run:  python demo_features.py
"""
import sys
from decimal import Decimal
sys.path.insert(0, ".")

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from models.account import Base, Account, AccountType
import models.account, models.ledger_entry
from models.ledger_entry import LedgerEntry
from services.pot_service import create_pot
from services.feature_service import (
    round_up_save, contribute_to_split, split_breakdown, can_i_afford,
)

LINE = "-" * 64

def banner(txt):
    print("\n" + "=" * 64); print(txt); print("=" * 64)

def seed_balance(db, user_id, amount):
    acc = Account(user_id=user_id, account_type=AccountType.BALANCE, currency="INR",
                  name=f"User {user_id} balance", balance=Decimal(amount))
    db.add(acc); db.flush(); return acc

# fresh in-memory DB so the demo is repeatable
engine = create_engine("sqlite:///./demo.db", connect_args={"check_same_thread": False})
Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
db = sessionmaker(bind=engine)()

# ─────────────────────────────────────────────────────────────────────────────
banner("FEATURE 1  —  ROUND-UP SAVES  (Gen Z)")
print("Riya has Rs 5,000 free. She buys a coffee for Rs 247.")
riya = seed_balance(db, user_id=1, amount="5000")
laptop = create_pot(db, user_id=1, currency="INR", name="Laptop Fund", target_amount=Decimal("80000"))
db.commit()
print(f"  Before:  balance Rs {riya.balance} | Laptop Fund Rs {laptop.balance}")
r = round_up_save(db, riya.id, laptop.id, Decimal("247"), round_to=Decimal("10"))
db.commit()
print(LINE)
print(f"  She spends Rs {r['spend']}  ->  rounds up to Rs {r['rounded_to']}")
print(f"  Spare change saved automatically:  Rs {r['spare_saved']}")
db.refresh(riya); db.refresh(laptop)
print(f"  After:   balance Rs {riya.balance} | Laptop Fund Rs {laptop.balance}")
print("  >> The Rs 3 moved through the SAME ledger as every other transaction.")

# ─────────────────────────────────────────────────────────────────────────────
banner("FEATURE 2  —  SPLIT-A-POT WITH FRIENDS  (Gen Z)")
print("Riya, Aman and Kai save together for a Goa trip in one shared pot.")
aman = seed_balance(db, user_id=2, amount="5000")
kai  = seed_balance(db, user_id=3, amount="5000")
trip = create_pot(db, user_id=1, currency="INR", name="Goa Trip (shared)", target_amount=Decimal("15000"))
db.commit()
contribute_to_split(db, riya.id, trip.id, Decimal("2000"))
contribute_to_split(db, aman.id, trip.id, Decimal("2000"))
contribute_to_split(db, kai.id,  trip.id, Decimal("1000"))
db.commit(); db.refresh(trip)
print(f"  Shared pot balance:  Rs {trip.balance}")
print(LINE)
print("  Who put what (straight from the ledger, provable to the rupee):")
for row in split_breakdown(db, trip.id):
    print(f"    User {row['owner_user_id']}  ->  Rs {row['contributed']}")
print("  >> Nobody can pull out more than they put in. The ledger is the truth.")

# ─────────────────────────────────────────────────────────────────────────────
banner("FEATURE 3  —  'CAN I AFFORD THIS?'  (AI)")
print("Riya wants Rs 12,000 headphones. She asks AIPA before buying.")
db.refresh(riya)
print(f"  Her free balance: Rs {riya.balance} | Goal: {laptop.name}")
print(LINE)
ans = can_i_afford(db, user_id=1, balance_account_id=riya.id,
                   purchase_amount=Decimal("12000"), goal_pot_id=laptop.id,
                   monthly_saving=Decimal("6000"))
print(f"  You ask:   {ans['question']}")
print(f"  AIPA says: {ans['aipa_says']}")
print(f"  Money moved by AIPA:  {ans['money_moved']}  (it only advises — you decide)")

# ─────────────────────────────────────────────────────────────────────────────
banner("PROOF  —  THE BOOKS STILL BALANCE")
total_balance = db.execute(select(func.sum(Account.balance)).where(Account.account_type==AccountType.BALANCE)).scalar()
total_pots    = db.execute(select(func.sum(Account.balance)).where(Account.account_type==AccountType.POT)).scalar()
total_seeded  = Decimal("15000")  # 5000 x 3 users
print(f"  Money in balances: Rs {total_balance}")
print(f"  Money in pots:     Rs {total_pots}")
print(f"  Total in system:   Rs {Decimal(str(total_balance)) + Decimal(str(total_pots))}")
print(f"  Total seeded in:   Rs {total_seeded}")
assert Decimal(str(total_balance)) + Decimal(str(total_pots)) == total_seeded
print("  >> Every rupee accounted for. Nothing created, nothing lost.")
print("\nDEMO COMPLETE — all three features ran on the real ledger.\n")
db.close()
