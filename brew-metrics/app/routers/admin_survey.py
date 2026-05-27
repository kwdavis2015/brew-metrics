from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.auth import require_admin
from app.db import get_db_conn

router = APIRouter()


@router.get("/admin/survey", response_class=HTMLResponse)
def admin_survey(request: Request, conn=Depends(get_db_conn), _=Depends(require_admin)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "admin/survey.html", {
        "people": queries.get_all_people(conn),
        "responses": queries.get_survey_responses(conn),
    })


@router.post("/admin/survey/assign")
def assign_team(
    conn=Depends(get_db_conn),
    _=Depends(require_admin),
    person_id: int = Form(...),
    team_name: str = Form(""),
):
    queries.assign_team(conn, person_id, team_name if team_name else None)
    return RedirectResponse("/admin/survey", status_code=303)


@router.post("/admin/survey/finalize")
def finalize_teams(conn=Depends(get_db_conn), _=Depends(require_admin)):
    queries.finalize_teams(conn)
    return RedirectResponse("/admin/survey", status_code=303)


@router.post("/admin/survey/add-person")
def add_person(
    conn=Depends(get_db_conn),
    _=Depends(require_admin),
    full_name: str = Form(...),
    nickname: str = Form(""),
    team_name: str = Form(""),
):
    queries.create_person(conn, full_name, nickname, team_name if team_name else None)
    return RedirectResponse("/admin/survey", status_code=303)
