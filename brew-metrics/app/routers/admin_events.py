from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.auth import require_admin
from app.db import get_db_conn

router = APIRouter()


@router.get("/admin/events", response_class=HTMLResponse)
def admin_events(request: Request, conn=Depends(get_db_conn), _=Depends(require_admin)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "admin/events.html", {
        "events": queries.get_events(conn),
    })


@router.post("/admin/events/score")
def save_event_score(
    conn=Depends(get_db_conn),
    _=Depends(require_admin),
    event_id: int = Form(...),
    riks_points: int = Form(...),
    wades_points: int = Form(...),
):
    queries.save_event_score(conn, event_id, riks_points, wades_points)
    return RedirectResponse("/admin/events", status_code=303)
