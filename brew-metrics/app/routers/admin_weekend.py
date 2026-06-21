from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.auth import require_admin
from app.db import get_db_conn

router = APIRouter()


@router.get("/admin/weekend", response_class=HTMLResponse)
def admin_weekend_page(request: Request, conn=Depends(get_db_conn), _=Depends(require_admin)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "admin/weekend.html", {
        "weekend_started": queries.get_weekend_started(conn),
    })


@router.post("/admin/weekend/kickoff")
def set_kickoff(
    conn=Depends(get_db_conn),
    _=Depends(require_admin),
    started: str = Form(...),
):
    queries.set_weekend_started(conn, started == "true")
    return RedirectResponse("/admin/weekend", status_code=303)


@router.post("/admin/weekend/reset")
def reset_data(conn=Depends(get_db_conn), _=Depends(require_admin)):
    queries.reset_weekend_data(conn)
    return RedirectResponse("/admin/weekend", status_code=303)
