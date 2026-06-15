from fastapi import APIRouter, Depends, Form, Request
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
    })


@router.post("/log-brew", response_class=HTMLResponse)
def log_brew_post(request: Request, conn=Depends(get_db_conn), person_id: int = Form(...)):
    templates = request.app.state.templates
    _, error, person = queries.log_brew(conn, person_id)
    return templates.TemplateResponse(request, "participant.html", {
        "people": queries.get_active_people(conn),
        "selected_person": person,
        "personal_count": queries.get_person_brews(conn, person_id),
        "keg_state": queries.get_keg_state(conn),
        "error": error,
    })
