from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import (
    COOKIE_NAME,
    check_credentials,
    create_token,
    set_admin_cookie,
    verify_token,
)

router = APIRouter()


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_form(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if token and verify_token(token):
        return RedirectResponse("/admin/survey", status_code=303)
    templates = request.app.state.templates
    error = request.query_params.get("error")
    return templates.TemplateResponse(request, "admin/login.html", {
        "error": error,
    })


@router.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    if not check_credentials(username, password):
        return RedirectResponse("/admin/login?error=1", status_code=303)
    token = create_token(username)
    response = RedirectResponse("/admin/survey", status_code=303)
    set_admin_cookie(response, token)
    return response
