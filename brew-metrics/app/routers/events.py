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
    })


@router.post("/events/score")
def submit_event_score(
    conn=Depends(get_db_conn),
    event_id: int = Form(...),
    team_1_points: str = Form(""),
    team_2_points: str = Form(""),
    person_id: str = Form(""),
):
    pid = parse_nonneg_int(person_id)
    if pid is None:
        return RedirectResponse("/events?error=no_person", status_code=303)
    p1 = parse_nonneg_int(team_1_points)
    p2 = parse_nonneg_int(team_2_points)
    if p1 is None or p2 is None:
        return RedirectResponse("/events?error=invalid_score", status_code=303)
    person = queries.get_person(conn, pid)
    entered_by = person["nickname"] or person["full_name"] if person else "unknown"
    queries.save_event_score(conn, event_id, p1, p2, entered_by)
    return RedirectResponse("/events", status_code=303)
