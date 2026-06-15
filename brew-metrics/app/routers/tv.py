from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app import queries
from app.db import get_db_conn

router = APIRouter()


@router.get("/tv", response_class=HTMLResponse)
def tv_dashboard(request: Request, conn=Depends(get_db_conn)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "tv.html", {
        "teams": queries.get_team_names(conn),
        "scores": queries.get_team_scores(conn),
        "events": queries.get_events(conn),
        "keg_state": queries.get_keg_state(conn),
        "leaderboard": queries.get_leaderboard(conn),
    })
