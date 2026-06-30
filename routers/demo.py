"""
IB Bud — live demo page (browser).  Open http://127.0.0.1:8000/demo

A clickable page that runs the three demo features against the REAL ledger.
Every button hits a real endpoint, real money moves through services.ledger_service,
and the page shows balances + a 'books balance' proof updating live.

Demo data is namespaced to user ids 9001/9002/9003 and pot names prefixed 'DEMO:',
so Reset never touches real wallet data.
"""
from decimal import Decimal
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from db.session import get_db, engine
from models.account import Base, Account, AccountType
from models.ledger_entry import LedgerEntry
from services.pot_service import create_pot
from services.feature_service import (
    round_up_save, contribute_to_split, split_breakdown, can_i_afford,
)

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_USERS = {9001: "Riya", 9002: "Aman", 9003: "Kai"}
SEED = Decimal("5000")


def _ensure_tables():
    Base.metadata.create_all(bind=engine)


def _demo_account_ids(db):
    return [a.id for a in db.execute(
        select(Account).where(Account.user_id.in_(DEMO_USERS.keys()))
    ).scalars().all()]


def _reset(db: Session):
    _ensure_tables()
    ids = _demo_account_ids(db)
    if ids:
        db.query(LedgerEntry).filter(
            or_(LedgerEntry.debit_account_id.in_(ids), LedgerEntry.credit_account_id.in_(ids))
        ).delete(synchronize_session=False)
        db.query(Account).filter(Account.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    accts = {}
    for uid, name in DEMO_USERS.items():
        a = Account(user_id=uid, account_type=AccountType.BALANCE, currency="INR",
                    name=f"{name} balance", balance=SEED)
        db.add(a); accts[uid] = a
    db.flush()
    laptop = create_pot(db, user_id=9001, currency="INR", name="DEMO: Laptop Fund", target_amount=Decimal("80000"))
    trip = create_pot(db, user_id=9001, currency="INR", name="DEMO: Goa Trip (shared)", target_amount=Decimal("15000"))
    db.commit()
    return accts, laptop, trip


def _ids(db):
    """Return the demo account/pot ids the page needs."""
    riya = db.execute(select(Account).where(Account.user_id==9001, Account.account_type==AccountType.BALANCE)).scalar_one()
    aman = db.execute(select(Account).where(Account.user_id==9002, Account.account_type==AccountType.BALANCE)).scalar_one()
    kai  = db.execute(select(Account).where(Account.user_id==9003, Account.account_type==AccountType.BALANCE)).scalar_one()
    laptop = db.execute(select(Account).where(Account.name=="DEMO: Laptop Fund")).scalar_one()
    trip = db.execute(select(Account).where(Account.name=="DEMO: Goa Trip (shared)")).scalar_one()
    return riya, aman, kai, laptop, trip


def _state(db: Session):
    _ensure_tables()
    if not _demo_account_ids(db):
        _reset(db)
    riya, aman, kai, laptop, trip = _ids(db)
    bal_total = db.execute(select(func.sum(Account.balance)).where(
        Account.user_id.in_(DEMO_USERS.keys()), Account.account_type==AccountType.BALANCE)).scalar() or Decimal("0")
    pot_total = db.execute(select(func.sum(Account.balance)).where(
        Account.name.in_(["DEMO: Laptop Fund","DEMO: Goa Trip (shared)"]))).scalar() or Decimal("0")
    total = Decimal(str(bal_total)) + Decimal(str(pot_total))
    seeded = SEED * len(DEMO_USERS)
    return {
        "riya_balance": str(riya.balance),
        "laptop_balance": str(laptop.balance),
        "laptop_target": str(laptop.target_amount),
        "laptop_pct": round(float(laptop.balance)/float(laptop.target_amount)*100, 1) if laptop.target_amount else 0,
        "trip_balance": str(trip.balance),
        "trip_breakdown": [
            {"name": DEMO_USERS.get(b["owner_user_id"], f"User {b['owner_user_id']}"), "amount": b["contributed"]}
            for b in split_breakdown(db, trip.id)
        ],
        "in_system": str(total),
        "seeded": str(seeded),
        "balances_ok": total == seeded,
    }


class RoundupBody(BaseModel): spend: float
class SplitBody(BaseModel): who: str; amount: float
class AffordBody(BaseModel): amount: float


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    _reset(db)
    return _state(db)


@router.get("/state")
def state(db: Session = Depends(get_db)):
    return _state(db)


@router.post("/roundup")
def roundup(body: RoundupBody, db: Session = Depends(get_db)):
    riya, aman, kai, laptop, trip = _ids(db)
    res = round_up_save(db, riya.id, laptop.id, Decimal(str(body.spend)), round_to=Decimal("10"))
    db.commit()
    return {"result": res, "state": _state(db)}


@router.post("/split")
def split(body: SplitBody, db: Session = Depends(get_db)):
    riya, aman, kai, laptop, trip = _ids(db)
    acct = {"Riya": riya, "Aman": aman, "Kai": kai}[body.who]
    contribute_to_split(db, acct.id, trip.id, Decimal(str(body.amount)))
    db.commit()
    return {"state": _state(db)}


@router.post("/afford")
def afford(body: AffordBody, db: Session = Depends(get_db)):
    riya, aman, kai, laptop, trip = _ids(db)
    ans = can_i_afford(db, user_id=9001, balance_account_id=riya.id,
                       purchase_amount=Decimal(str(body.amount)), goal_pot_id=laptop.id,
                       monthly_saving=Decimal("6000"))
    return {"answer": ans, "state": _state(db)}


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def page():
    return HTML


HTML = """
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IB Bud — Live Demo</title>
<style>
 *{box-sizing:border-box;margin:0;padding:0}
 body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0B1B2B;color:#10241a;
      display:flex;justify-content:center;padding:24px}
 .phone{width:100%;max-width:430px;background:#F6F8F7;border-radius:22px;overflow:hidden;
        box-shadow:0 12px 40px rgba(0,0,0,.35)}
 .top{background:#0F6E56;color:#fff;padding:18px 20px}
 .top h1{font-size:19px;font-weight:700}
 .top p{font-size:12px;opacity:.85;margin-top:3px}
 .wrap{padding:16px}
 .card{background:#fff;border:1px solid #E3E8E5;border-radius:14px;padding:15px;margin-bottom:14px}
 .card h2{font-size:15px;color:#0B1B2B;margin-bottom:2px}
 .tag{display:inline-block;font-size:10px;font-weight:700;padding:2px 7px;border-radius:8px;margin-left:6px;vertical-align:middle}
 .t-genz{background:#E1F5EE;color:#0F6E56}.t-ai{background:#EEEDFE;color:#534AB7}
 .sub{font-size:12px;color:#5F5E5A;margin:4px 0 12px}
 .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
 input{flex:1;min-width:80px;padding:9px 10px;border:1px solid #D7DEDB;border-radius:9px;font-size:14px}
 button{background:#0F6E56;color:#fff;border:0;padding:9px 14px;border-radius:9px;font-size:13px;font-weight:600;cursor:pointer}
 button:active{transform:scale(.97)}
 button.gray{background:#fff;color:#0F6E56;border:1px solid #0F6E56}
 button.pur{background:#534AB7}
 .pill{display:inline-block;background:#F1EFE8;color:#444;font-size:11px;padding:3px 8px;border-radius:8px;margin:3px 4px 0 0}
 .bar{height:9px;background:#EEF1EF;border-radius:6px;overflow:hidden;margin-top:8px}
 .bar > i{display:block;height:100%;background:#0F6E56}
 .stat{display:flex;justify-content:space-between;font-size:13px;padding:4px 0}
 .stat b{color:#0B1B2B}
 .msg{font-size:13px;background:#EEEDFE;color:#2c2660;border-radius:9px;padding:10px;margin-top:10px;display:none}
 .proof{background:#0B1B2B;color:#fff;border-radius:14px;padding:14px;margin-top:4px}
 .proof .ok{color:#9FE1CB;font-weight:700}
 .proof .small{font-size:11px;opacity:.8;margin-top:4px}
 .feed{font-size:12px;color:#1E7F34;margin-top:8px;min-height:16px}
</style></head><body>
<div class="phone">
 <div class="top"><h1>IB Bud — Wallet</h1><p>Live demo · real money, real ledger</p></div>
 <div class="wrap">

  <div class="card">
   <h2>Round-up saves <span class="tag t-genz">GEN Z</span></h2>
   <div class="sub">Spend something. The spare change rounds up into your Laptop Fund.</div>
   <div class="row">
     <input id="spend" type="number" value="247" min="1">
     <button onclick="roundup()">Spend &amp; round up</button>
   </div>
   <div class="feed" id="roundup-feed"></div>
   <div class="stat"><span>Riya's balance</span><b id="riya-bal">—</b></div>
   <div class="stat"><span>Laptop Fund</span><b id="laptop-bal">—</b></div>
   <div class="bar"><i id="laptop-bar" style="width:0%"></i></div>
   <div class="sub" id="laptop-pct" style="margin-top:6px">—</div>
  </div>

  <div class="card">
   <h2>Split-a-pot with friends <span class="tag t-genz">GEN Z</span></h2>
   <div class="sub">Everyone chips into one shared Goa Trip pot. It tracks who put what.</div>
   <div class="row">
     <input id="split-amt" type="number" value="2000" min="1">
     <button onclick="split('Riya')">Riya</button>
     <button onclick="split('Aman')">Aman</button>
     <button onclick="split('Kai')">Kai</button>
   </div>
   <div class="stat" style="margin-top:8px"><span>Shared pot</span><b id="trip-bal">—</b></div>
   <div id="trip-breakdown"></div>
  </div>

  <div class="card">
   <h2>Can I afford this? <span class="tag t-ai">AI</span></h2>
   <div class="sub">Ask AIPA before a big buy. It checks your money and answers. No money moves.</div>
   <div class="row">
     <input id="afford-amt" type="number" value="12000" min="1">
     <button class="pur" onclick="afford()">Ask AIPA</button>
   </div>
   <div class="msg" id="afford-msg"></div>
  </div>

  <div class="proof">
   <div class="stat" style="color:#fff"><span>Money in the system</span><b id="in-system">—</b></div>
   <div class="stat" style="color:#fff"><span>Money put in</span><b id="seeded">—</b></div>
   <div id="proof-line" class="ok">—</div>
   <div class="small">Every rupee accounted for. Fun features, nothing lost.</div>
   <div style="margin-top:10px"><button class="gray" onclick="reset()">Reset demo</button></div>
  </div>

 </div>
</div>
<script>
const $ = id => document.getElementById(id);
function paint(s){
  $('riya-bal').textContent   = 'Rs ' + s.riya_balance;
  $('laptop-bal').textContent = 'Rs ' + s.laptop_balance;
  $('laptop-bar').style.width = Math.min(100, s.laptop_pct) + '%';
  $('laptop-pct').textContent = s.laptop_pct + '% of Rs ' + s.laptop_target;
  $('trip-bal').textContent   = 'Rs ' + s.trip_balance;
  $('trip-breakdown').innerHTML = s.trip_breakdown.map(b => '<span class="pill">'+b.name+': Rs '+b.amount+'</span>').join('');
  $('in-system').textContent  = 'Rs ' + s.in_system;
  $('seeded').textContent     = 'Rs ' + s.seeded;
  $('proof-line').textContent = s.balances_ok ? '\u2713 Books balance to the rupee' : '\u2717 DRIFT DETECTED';
}
async function load(){ paint(await (await fetch('/demo/state')).json()); }
async function roundup(){
  const r = await (await fetch('/demo/roundup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({spend:+$('spend').value})})).json();
  const res = r.result;
  $('roundup-feed').textContent = res.spare_saved && res.spare_saved!=='0.00'
     ? 'Spent Rs '+res.spend+' \u2192 rounded to Rs '+res.rounded_to+' \u2192 saved Rs '+res.spare_saved
     : 'Already a round number — nothing to round.';
  paint(r.state);
}
async function split(who){
  const r = await (await fetch('/demo/split',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({who:who,amount:+$('split-amt').value})})).json();
  paint(r.state);
}
async function afford(){
  const r = await (await fetch('/demo/afford',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({amount:+$('afford-amt').value})})).json();
  const m = $('afford-msg'); m.style.display='block';
  m.innerHTML = '<b>You:</b> Can I afford Rs '+(+$('afford-amt').value)+'?<br><b>AIPA:</b> '+r.answer.aipa_says;
  paint(r.state);
}
async function reset(){ paint(await (await fetch('/demo/reset',{method:'POST'})).json()); $('afford-msg').style.display='none'; $('roundup-feed').textContent=''; }
load();
</script>
</body></html>
"""
