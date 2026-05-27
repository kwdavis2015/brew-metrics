from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.auth import require_admin
from app.db import get_db_conn

router = APIRouter()


@router.get("/admin/brews", response_class=HTMLResponse)
def admin_brews(request: Request, conn=Depends(get_db_conn), _=Depends(require_admin)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "admin/brews.html", {
        "brew_log": queries.get_brew_log(conn),
        "people": queries.get_active_people(conn),
        "keg_state": queries.get_keg_state(conn),
    })


@router.post("/admin/brews/reverse")
def reverse_brew(conn=Depends(get_db_conn), _=Depends(require_admin), entry_id: int = Form(...)):
    queries.reverse_brew(conn, entry_id)
    return RedirectResponse("/admin/brews", status_code=303)
