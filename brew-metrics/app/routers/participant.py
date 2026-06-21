from html import escape

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse

from app import queries
from app.db import get_db_conn

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def participant_page(request: Request, conn=Depends(get_db_conn)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "participant.html", {
        "people": queries.get_active_people(conn),
        "selected_person": None,
        "personal_count": 0,
        "keg_state": queries.get_keg_state(conn),
        "error": None,
        "weekend_started": queries.get_weekend_started(conn),
    })


@router.post("/log-brew", response_class=HTMLResponse)
def log_brew_post(
    request: Request,
    conn=Depends(get_db_conn),
    person_id: int = Form(...),
    source: str = Form("keg"),
):
    templates = request.app.state.templates
    if not queries.get_weekend_started(conn):
        return templates.TemplateResponse(request, "participant.html", {
            "people": queries.get_active_people(conn),
            "selected_person": None,
            "personal_count": 0,
            "keg_state": queries.get_keg_state(conn),
            "error": None,
            "weekend_started": False,
        })
    source = source if source in ("keg", "byob") else "keg"
    _, error, person = queries.log_brew(conn, person_id, source)
    return templates.TemplateResponse(request, "participant.html", {
        "people": queries.get_active_people(conn),
        "selected_person": person,
        "personal_count": queries.get_person_brews(conn, person_id),
        "keg_state": queries.get_keg_state(conn),
        "error": error,
        "weekend_started": True,
    })


@router.get("/api/me", response_class=HTMLResponse)
def me_banner(conn=Depends(get_db_conn), person_id: int | None = Query(default=None)):
    if not person_id:
        return ""
    person = queries.get_person(conn, person_id)
    if not person or person["status"] != "active":
        return ""
    count = queries.get_person_brews(conn, person_id)
    name = escape(person["nickname"] or person["full_name"])
    return (
        f'<span class="me-name">{name}</span>'
        f'<span class="me-sep">·</span>'
        f'<span class="me-count">🍺 {count}</span>'
    )
