import os
from pathlib import Path

import psycopg2
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://brewadmin:localdev@localhost:5432/brewmetrics")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("DOSSIER_KEY", "test-dossier-key")

_SCHEMA = (Path(__file__).parent.parent / "app" / "schema.sql").read_text()


@pytest.fixture(scope="session")
def _admin_conn():
    """One autocommit connection for the whole run, used for schema + cleanup."""
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def _db_setup(_admin_conn):
    """Build schema and the app connection pool once per session."""
    from app.db import close_pool, init_pool

    cur = _admin_conn.cursor()
    # Terminate other connections (e.g. app container pool) so DROP TABLE doesn't wait
    cur.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = current_database() AND pid <> pg_backend_pid()"
    )
    cur.execute(
        "DROP TABLE IF EXISTS admin_adjustments, event_results, event_round_results, event_master, "
        "brew_log, team_keg_state, erik_dossier_responses, team_survey_responses, people, teams CASCADE"
    )
    cur.execute(_SCHEMA)
    cur.close()

    init_pool()
    yield
    close_pool()


@pytest.fixture(autouse=True)
def _clean_db(_admin_conn):
    cur = _admin_conn.cursor()
    cur.execute(
        "TRUNCATE admin_adjustments, event_results, event_round_results, brew_log, "
        "team_keg_state, erik_dossier_responses, team_survey_responses, people, teams RESTART IDENTITY CASCADE"
    )
    cur.execute("INSERT INTO teams (name) VALUES ('Riks'), ('Wades')")
    cur.execute("INSERT INTO team_keg_state (team_name) VALUES ('Riks'), ('Wades')")
    # event_master is catalog data (not truncated), but its status is mutable —
    # reset it so per-event status changes don't leak between tests.
    cur.execute("UPDATE event_master SET status = 'pending'")
    cur.execute("UPDATE app_settings SET value = 'false' WHERE key = 'weekend_started'")
    cur.close()
    yield


@pytest.fixture
def client():
    # No `with` block: lifespan stays off, so the session-scoped pool isn't
    # re-created per test. Routes use the global pool + app.state.templates.
    from app.main import app

    return TestClient(app)


@pytest.fixture
def admin_client(client):
    client.post("/admin/login", data={"username": "admin", "password": "admin"})
    return client


def seed_teams(conn, team_1="Riks", team_2="Wades"):
    # The two fixed teams are already seeded by _clean_db; these inserts are
    # no-ops via ON CONFLICT. Returning the names lets tests use them as the
    # canonical team handles without assuming any extra teams exist.
    cur = conn.cursor()
    cur.execute("INSERT INTO teams (name) VALUES (%s), (%s) ON CONFLICT DO NOTHING", (team_1, team_2))
    cur.execute(
        "INSERT INTO team_keg_state (team_name) VALUES (%s), (%s) ON CONFLICT DO NOTHING",
        (team_1, team_2),
    )
    conn.commit()
    cur.close()
    return team_1, team_2


def seed_person(conn, full_name, nickname=None, team_name=None, status="active"):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO people (full_name, nickname, team_name, status) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (full_name, nickname, team_name, status),
    )
    pid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return pid


@pytest.fixture
def seeded_db():
    db_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(db_url)
    t1, t2 = seed_teams(conn)
    seed_person(conn, "Mike Davis", "MikeD", t1, "active")
    seed_person(conn, "Steve Parker", None, t2, "active")
    seed_person(conn, "Alex Reed", None, None, "pre_registered")
    conn.close()
    return t1, t2
