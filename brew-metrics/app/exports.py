"""CSV download helpers shared by the metrics and survey export routes."""
import csv
import io
from datetime import date, datetime

from fastapi.responses import Response


def _format_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if value is None:
        return ""
    return value


def rows_to_csv(rows: list[dict], columns: list[str]) -> str:
    """Render dict rows to CSV text using only the given columns, in order."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: _format_value(row.get(col)) for col in columns})
    return buf.getvalue()


def csv_response(rows: list[dict], columns: list[str], filename_stem: str) -> Response:
    """Build an attachment CSV response with a date-stamped filename."""
    body = rows_to_csv(rows, columns)
    filename = f"{filename_stem}-{date.today().isoformat()}.csv"
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
