from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app import queries
from app.db import get_db_conn

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, conn=Depends(get_db_conn)):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "dashboard.html", queries.get_dashboard_context(conn)
    )
