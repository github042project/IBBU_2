from fastapi import FastAPI

from routers.aipa import router as aipa_router
from routers.pots import router as pots_router
from routers.reconcile import router as reconcile_router
from routers.demo import router as demo_router
from fastapi.staticfiles import StaticFiles
from routers.dream_ui import router as dream_ui_router
from routers.dream import router as dream_router

app = FastAPI(title="IB Wallet")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pots_router)
app.include_router(reconcile_router)
app.include_router(aipa_router)
app.include_router(demo_router)
app.include_router(dream_router)
app.include_router(dream_ui_router)

@app.get("/health")
def health():
    return {"status": "ok"}