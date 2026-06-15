from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import queries
from app.auth import require_admin
from app.db import get_db_conn

router = APIRouter()


@router.get("/admin/teams", response_class=HTMLResponse)
def admin_teams(request: Request, conn=Depends(get_db_conn), _=Depends(require_admin)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "admin/teams.html", {
        "teams": queries.get_teams(conn),
        "max_teams": queries.MAX_TEAMS,
    })


@router.post("/admin/teams/create")
def create_team(
    conn=Depends(get_db_conn),
    _=Depends(require_admin),
    name: str = Form(...),
):
    queries.create_team(conn, name.strip())
    return RedirectResponse("/admin/teams", status_code=303)
