from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.constants import SKILLS
from app.db import get_db_conn

router = APIRouter()


@router.get("/survey", response_class=HTMLResponse)
def survey_form(request: Request):
    templates = request.app.state.templates
    submitted = request.query_params.get("submitted")
    return templates.TemplateResponse(request, "survey.html", {
        "skills": SKILLS,
        "submitted": submitted,
    })


@router.post("/survey")
def survey_submit(
    conn=Depends(get_db_conn),
    full_name: str = Form(...),
    nickname: str = Form(""),
    expected_arrival_day: str = Form(...),
    expected_arrival_time: str = Form(""),
    skill_1: str = Form(""),
    skill_2: str = Form(""),
    skill_3: str = Form(""),
    brew_drinking_skill_rank: int = Form(2),
    notes: str = Form(""),
):
    queries.create_survey_submission(
        conn, full_name, nickname, expected_arrival_day, expected_arrival_time,
        skill_1, skill_2, skill_3, brew_drinking_skill_rank, notes,
    )
    return RedirectResponse("/survey?submitted=1", status_code=303)
