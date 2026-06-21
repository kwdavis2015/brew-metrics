"""
Lightweight Flyway-style migration runner.

Discovers V{N}__{description}.sql files under db/migrations/, applies them
in version order, and records each in a schema_migrations tracking table
(mirroring Flyway's flyway_schema_history). Each migration runs inside its
own transaction: if it fails the migration rolls back and the app refuses to
start, keeping the DB in the last known-good state.

File naming: V1__initial_schema.sql, V2__event_round_results.sql, …
Version numbers may be integers or dotted integers (V1_1, V2_3).
"""

import hashlib
import logging
import os
import re
import time
from pathlib import Path

import psycopg2

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"

_FILENAME_RE = re.compile(r"V(\d+(?:_\d+)*)__(.+)\.sql$")


def _version_key(path: Path) -> tuple[int, ...]:
    m = _FILENAME_RE.match(path.name)
    if not m:
        raise ValueError(f"Migration filename does not match V{{N}}__{{desc}}.sql: {path.name}")
    return tuple(int(x) for x in m.group(1).split("_"))


def _checksum(sql: str) -> str:
    normalized = sql.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode()).hexdigest()


def run():
    """Apply all pending migrations. Safe to call on every app startup."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL not set — skipping migrations")
        return

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    try:
        _bootstrap(conn)
        applied = _applied_versions(conn)
        pending = _pending_migrations(applied)

        for path, version, description in pending:
            _apply(conn, path, version, description)

        total = len(list(MIGRATIONS_DIR.glob("V*.sql")))
        logger.info("Schema up to date (%d migration(s) total)", total)
    finally:
        conn.close()


def _bootstrap(conn) -> None:
    """Create the schema_migrations tracking table if it doesn't exist yet."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version      TEXT PRIMARY KEY,
                description  TEXT NOT NULL,
                checksum     TEXT NOT NULL,
                applied_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                execution_ms INTEGER
            )
        """)
    conn.commit()


def _applied_versions(conn) -> dict[str, str]:
    """Return {version: checksum} for every already-applied migration."""
    with conn.cursor() as cur:
        cur.execute("SELECT version, checksum FROM schema_migrations ORDER BY version")
        result = {r[0]: r[1] for r in cur.fetchall()}
    conn.commit()
    return result


def _pending_migrations(applied: dict[str, str]) -> list[tuple[Path, str, str]]:
    """Return (path, version, description) tuples for migrations not yet applied."""
    paths = sorted(
        [p for p in MIGRATIONS_DIR.glob("V*.sql") if _FILENAME_RE.match(p.name)],
        key=_version_key,
    )
    if not paths:
        logger.warning("No migration files found in %s", MIGRATIONS_DIR)
        return []

    pending = []
    for path in paths:
        m = _FILENAME_RE.match(path.name)
        version = m.group(1)
        description = m.group(2).replace("_", " ")

        if version in applied:
            # Verify the file hasn't been modified since it was applied
            stored = applied[version]
            current = _checksum(path.read_text())
            if stored != current:
                raise RuntimeError(
                    f"Checksum mismatch for V{version} ({path.name}): "
                    f"file was modified after being applied. "
                    f"stored={stored[:12]}… current={current[:12]}…"
                )
        else:
            pending.append((path, version, description))

    return pending


def _apply(conn, path: Path, version: str, description: str) -> None:
    """Run one migration inside a single transaction."""
    sql = path.read_text()
    checksum = _checksum(sql)

    logger.info("Applying V%s: %s", version, description)
    t0 = time.monotonic()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations (version, description, checksum, execution_ms) "
                "VALUES (%s, %s, %s, %s)",
                (version, description, checksum, int((time.monotonic() - t0) * 1000)),
            )
        conn.commit()
        logger.info("V%s applied in %dms", version, int((time.monotonic() - t0) * 1000))
    except Exception:
        conn.rollback()
        logger.error("Migration V%s FAILED — rolled back. App will not start.", version, exc_info=True)
        raise
