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

    cur.execute(
        "DROP TABLE IF EXISTS admin_adjustments, event_results, event_master, "
        "brew_log, team_keg_state, team_survey_responses, people, teams CASCADE"
    )

    schema = (Path(__file__).parent.parent / "app" / "schema.sql").read_text()
    cur.execute(schema)

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


def seed_teams(conn, team_1="Team Alpha", team_2="Team Beta"):
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
