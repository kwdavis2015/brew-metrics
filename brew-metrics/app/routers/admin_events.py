from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.auth import require_admin
from app.constants import EVENT_STATUSES
from app.db import get_db_conn
from app.forms import parse_nonneg_int

router = APIRouter()


@router.get("/admin/events", response_class=HTMLResponse)
def admin_events(request: Request, conn=Depends(get_db_conn), _=Depends(require_admin)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "admin/events.html", {
        "events": queries.get_events(conn),
        "teams": queries.get_team_names(conn),
        "statuses": EVENT_STATUSES,
        "error": request.query_params.get("error"),
    })


@router.post("/admin/events/score")
def save_event_score(
    conn=Depends(get_db_conn),
    admin=Depends(require_admin),
    event_id: int = Form(...),
    team_1_points: str = Form(""),
    team_2_points: str = Form(""),
):
    p1 = parse_nonneg_int(team_1_points)
    p2 = parse_nonneg_int(team_2_points)
    if p1 is None or p2 is None:
        return RedirectResponse("/admin/events?error=invalid_score", status_code=303)
    entered_by = f"admin:{admin['sub']}"
    queries.save_event_score(conn, event_id, p1, p2, entered_by)
    return RedirectResponse("/admin/events", status_code=303)


@router.post("/admin/events/status")
def update_event_status(
    conn=Depends(get_db_conn),
    _=Depends(require_admin),
    event_id: int = Form(...),
    status: str = Form(...),
):
    if not queries.set_event_status(conn, event_id, status):
        return RedirectResponse("/admin/events?error=invalid_status", status_code=303)
    return RedirectResponse("/admin/events", status_code=303)
