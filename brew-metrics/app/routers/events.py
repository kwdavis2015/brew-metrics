from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.db import get_db_conn
from app.forms import parse_nonneg_int

router = APIRouter()


@router.get("/events", response_class=HTMLResponse)
def events_page(request: Request, conn=Depends(get_db_conn)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "events.html", {
        "events": queries.get_events(conn),
        "teams": queries.get_team_names(conn),
        "people": queries.get_active_people(conn),
        "error": request.query_params.get("error"),
        "weekend_started": queries.get_weekend_started(conn),
    })


def _check_gate(conn, person_id: str, winner_team: str | None = None):
    """Returns (pid, error_code) — error_code is set if validation fails."""
    if not queries.get_weekend_started(conn):
        return None, "not_started"
    pid = parse_nonneg_int(person_id)
    if pid is None:
        return None, "no_person"
    if winner_team is not None:
        teams = queries.get_team_names(conn)
        if winner_team not in teams:
            return None, "invalid_team"
    return pid, None


@router.post("/events/winner")
def submit_event_winner(
    conn=Depends(get_db_conn),
    event_id: int = Form(...),
    winner_team: str = Form(...),
    person_id: str = Form(""),
):
    pid, err = _check_gate(conn, person_id, winner_team)
    if err:
        return RedirectResponse(f"/events?error={err}", status_code=303)
    person = queries.get_person(conn, pid)
    entered_by = person["nickname"] or person["full_name"] if person else "unknown"
    queries.save_event_winner(conn, event_id, winner_team, entered_by)
    return RedirectResponse("/events", status_code=303)


@router.post("/events/round")
def submit_event_round(
    conn=Depends(get_db_conn),
    event_id: int = Form(...),
    round_number: int = Form(...),
    winner_team: str = Form(...),
    person_id: str = Form(""),
):
    pid, err = _check_gate(conn, person_id, winner_team)
    if err:
        return RedirectResponse(f"/events?error={err}", status_code=303)
    if round_number not in (1, 2, 3):
        return RedirectResponse("/events?error=invalid_round", status_code=303)
    person = queries.get_person(conn, pid)
    entered_by = person["nickname"] or person["full_name"] if person else "unknown"
    queries.save_round_result(conn, event_id, round_number, winner_team, entered_by)
    return RedirectResponse("/events", status_code=303)


@router.post("/events/reset")
def reset_event(
    conn=Depends(get_db_conn),
    event_id: int = Form(...),
    person_id: str = Form(""),
):
    if not queries.get_weekend_started(conn):
        return RedirectResponse("/events?error=not_started", status_code=303)
    pid = parse_nonneg_int(person_id)
    if pid is None:
        return RedirectResponse("/events?error=no_person", status_code=303)
    queries.reset_event(conn, event_id)
    return RedirectResponse("/events", status_code=303)
