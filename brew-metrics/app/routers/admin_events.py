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
        "teams": queries.get_team_names(conn),
    })


@router.post("/admin/events/score")
def save_event_score(
    conn=Depends(get_db_conn),
    _=Depends(require_admin),
    event_id: int = Form(...),
    team_1_points: int = Form(...),
    team_2_points: int = Form(...),
):
    queries.save_event_score(conn, event_id, team_1_points, team_2_points)
    return RedirectResponse("/admin/events", status_code=303)
