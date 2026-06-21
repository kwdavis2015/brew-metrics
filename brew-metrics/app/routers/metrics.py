from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app import queries
from app.db import get_db_conn

router = APIRouter()

_SCALE_LABELS = {
    "weekend": "Per Day",
    "day": "Per Hour",
    "hour": "Per 15 Min",
}


@router.get("/metrics", response_class=HTMLResponse)
def metrics_page(
    request: Request,
    conn=Depends(get_db_conn),
    scale: str = Query(default="day"),
    group: str = Query(default="total"),
):
    if scale not in _SCALE_LABELS:
        scale = "day"
    if group not in ("total", "team", "person"):
        group = "total"
    timeseries = queries.get_brew_timeseries(conn, scale)
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "metrics.html", {
        "scale": scale,
        "group": group,
        "timeseries": timeseries,
        "avg_label": _SCALE_LABELS[scale],
    })
