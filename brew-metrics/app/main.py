from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import NotAuthenticatedError
from app.db import apply_schema, close_pool, init_pool
from app.routers import (
    admin,
    admin_brews,
    admin_events,
    admin_survey,
    dashboard,
    health,
    participant,
    survey,
    tv,
)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app):
    init_pool()
    apply_schema()
    yield
    close_pool()


app = FastAPI(title="brew-metrics", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.state.templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.exception_handler(NotAuthenticatedError)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedError):
    return RedirectResponse("/admin/login", status_code=303)


app.include_router(health.router)
app.include_router(participant.router)
app.include_router(survey.router)
app.include_router(dashboard.router)
app.include_router(tv.router)
app.include_router(admin.router)
app.include_router(admin_survey.router)
app.include_router(admin_brews.router)
app.include_router(admin_events.router)
