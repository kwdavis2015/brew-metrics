import os
from pathlib import Path

import psycopg2
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://brewadmin:localdev@localhost:5432/brewmetrics")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("JWT_SECRET", "test-secret")


@pytest.fixture(autouse=True)
def _clean_db():
    db_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    schema = (Path(__file__).parent.parent / "app" / "schema.sql").read_text()
    cur.execute(schema)

    cur.execute(
        "TRUNCATE people, team_survey_responses, brew_log, "
        "event_results, admin_adjustments CASCADE"
    )
    cur.execute(
        "DELETE FROM team_keg_state WHERE TRUE; "
        "INSERT INTO team_keg_state (team_name) VALUES ('Riks'), ('Wades')"
    )

    cur.close()
    conn.close()
    yield


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_client(client):
    client.post("/admin/login", data={"username": "admin", "password": "admin"})
    return client


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
    seed_person(conn, "Mike Davis", "MikeD", "Riks", "active")
    seed_person(conn, "Steve Parker", None, "Wades", "active")
    seed_person(conn, "Alex Reed", None, None, "pre_registered")
    conn.close()
