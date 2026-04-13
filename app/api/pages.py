from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.deps import get_optional_user
from app.models import User

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request, current_user: User | None = Depends(get_optional_user)):
    if not current_user:
        return templates.TemplateResponse(request, "login.html", {"request": request})
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "email": current_user.email,
            "role": current_user.role,
        },
    )
