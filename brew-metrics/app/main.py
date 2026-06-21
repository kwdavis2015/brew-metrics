from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import (
    COOKIE_NAME,
    NotAuthenticatedError,
    create_token,
    set_admin_cookie,
    verify_token,
)
from app.db import close_pool, init_pool
from app import migrate
from app.secrets import load_secrets
from app.routers import (
    admin,
    admin_brews,
    admin_dossier,
    admin_events,
    admin_survey,
    admin_weekend,
    dashboard,
    events,
    health,
    metrics,
    participant,
    survey,
    tv,
)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app):
    load_secrets()
    migrate.run()
    init_pool()
    yield
    close_pool()


app = FastAPI(title="brew-metrics", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.state.templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.exception_handler(NotAuthenticatedError)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedError):
    return RedirectResponse("/admin/login", status_code=303)


@app.middleware("http")
async def refresh_admin_session(request: Request, call_next):
    """Sliding session: re-issue the admin cookie on each authenticated
    /admin request so active use keeps extending the 8h window."""
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/admin") and not path.startswith("/admin/login"):
        token = request.cookies.get(COOKIE_NAME)
        if token:
            payload = verify_token(token)
            if payload and payload.get("sub"):
                set_admin_cookie(response, create_token(payload["sub"]))
    return response


app.include_router(health.router)
app.include_router(participant.router)
app.include_router(survey.router)
app.include_router(dashboard.router)
app.include_router(events.router)
app.include_router(tv.router)
app.include_router(admin.router)
app.include_router(admin_survey.router)
app.include_router(admin_brews.router)
app.include_router(admin_events.router)
app.include_router(admin_weekend.router)
app.include_router(admin_dossier.router)
app.include_router(metrics.router)
