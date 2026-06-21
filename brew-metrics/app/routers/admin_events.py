from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.auth import require_admin
from app.constants import EVENT_STATUSES
from app.db import get_db_conn
from app.forms import parse_pos_int

router = APIRouter()


@router.get("/admin/events", response_class=HTMLResponse)
def admin_events(request: Request, conn=Depends(get_db_conn), _=Depends(require_admin)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "admin/events.html", {
        "events": queries.get_events(conn),
        "teams": queries.get_team_names(conn),
        "statuses": EVENT_STATUSES,
        "adjustments": queries.get_admin_adjustments(conn),
        "error": request.query_params.get("error"),
    })


@router.post("/admin/events/winner")
def save_event_winner(
    conn=Depends(get_db_conn),
    admin=Depends(require_admin),
    event_id: int = Form(...),
    winner_team: str = Form(...),
):
    teams = queries.get_team_names(conn)
    if winner_team not in teams:
        return RedirectResponse("/admin/events?error=invalid_team", status_code=303)
    entered_by = f"admin:{admin['sub']}"
    queries.save_event_winner(conn, event_id, winner_team, entered_by)
    return RedirectResponse("/admin/events", status_code=303)


@router.post("/admin/events/round")
def save_round_result(
    conn=Depends(get_db_conn),
    admin=Depends(require_admin),
    event_id: int = Form(...),
    round_number: int = Form(...),
    winner_team: str = Form(...),
):
    teams = queries.get_team_names(conn)
    if winner_team not in teams:
        return RedirectResponse("/admin/events?error=invalid_team", status_code=303)
    if round_number not in (1, 2, 3):
        return RedirectResponse("/admin/events?error=invalid_round", status_code=303)
    entered_by = f"admin:{admin['sub']}"
    queries.save_round_result(conn, event_id, round_number, winner_team, entered_by)
    return RedirectResponse("/admin/events", status_code=303)


@router.post("/admin/events/reset")
def reset_event(
    conn=Depends(get_db_conn),
    _=Depends(require_admin),
    event_id: int = Form(...),
):
    queries.reset_event(conn, event_id)
    return RedirectResponse("/admin/events", status_code=303)


@router.post("/admin/events/deduct")
def add_cheat_deduction(
    conn=Depends(get_db_conn),
    admin=Depends(require_admin),
    team_name: str = Form(...),
    points: str = Form(""),
    reason: str = Form(""),
):
    pts = parse_pos_int(points)
    if pts is None:
        return RedirectResponse("/admin/events?error=invalid_deduction", status_code=303)
    if not reason.strip():
        return RedirectResponse("/admin/events?error=missing_reason", status_code=303)
    queries.add_cheat_deduction(conn, team_name, pts, reason.strip(), f"admin:{admin['sub']}")
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
