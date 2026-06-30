"""Serves the IB Dream demo UI page. Frontend only — no business logic."""
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["IB Dream — Demo UI"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/dream-ui")
def dream_ui(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dream_demo.html"
    )
