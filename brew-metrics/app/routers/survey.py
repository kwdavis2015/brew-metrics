from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.constants import BEER_LEVELS, SKILLS
from app.db import get_db_conn

router = APIRouter()


@router.get("/survey", response_class=HTMLResponse)
def survey_form(request: Request):
    templates = request.app.state.templates
    submitted = request.query_params.get("submitted")
    return templates.TemplateResponse(request, "survey.html", {
        "skills": SKILLS,
        "beer_levels": BEER_LEVELS,
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
    brew_drinking_level: str = Form(""),
    notes: str = Form(""),
    beers_pledged: str = Form(""),
    score_prediction_riks: str = Form(""),
    score_prediction_wades: str = Form(""),
    first_to_puke: str = Form(""),
    first_to_tap_out: str = Form(""),
    best_erik_story: str = Form(""),
    erik_in_one_word: str = Form(""),
    eriks_nickname: str = Form(""),
    over_under_marriage: str = Form(""),
):
    def to_int(val: str):
        try:
            return int(val) if val.strip() else None
        except (ValueError, AttributeError):
            return None

    queries.create_survey_submission(
        conn, full_name, nickname, expected_arrival_day, expected_arrival_time,
        skill_1, skill_2, skill_3, brew_drinking_level, notes,
        to_int(beers_pledged), to_int(score_prediction_riks), to_int(score_prediction_wades),
        first_to_puke, first_to_tap_out,
        best_erik_story, erik_in_one_word, eriks_nickname, over_under_marriage,
    )
    return RedirectResponse("/survey?submitted=1", status_code=303)
