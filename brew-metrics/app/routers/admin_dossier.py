import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app import queries
from app.db import get_db_conn

router = APIRouter()


@router.get("/admin/dossier", response_class=HTMLResponse)
def dossier_view(request: Request, key: str = "", conn=Depends(get_db_conn)):
    dossier_key = os.environ.get("DOSSIER_KEY", "")
    if dossier_key and key != dossier_key:
        raise HTTPException(status_code=403, detail="Forbidden")
    templates = request.app.state.templates
    responses = queries.get_dossier_responses(conn)
    return templates.TemplateResponse(request, "admin/dossier.html", {
        "responses": responses,
    })
