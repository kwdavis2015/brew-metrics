import os

import psycopg2
import pytest

from app.forms import parse_nonneg_int


@pytest.fixture(autouse=True)
def _weekend_on(_admin_conn):
    cur = _admin_conn.cursor()
    cur.execute("UPDATE app_settings SET value = 'true' WHERE key = 'weekend_started'")
    cur.close()


def _get_event_id(name="Cornhole"):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = %s", (name,))
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()
    return eid


def _get_person_id(full_name="Mike Davis"):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = %s", (full_name,))
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()
    return pid


def _result_row(eid):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
        "SELECT team_1_points, team_2_points, entered_by FROM event_results WHERE event_id = %s",
        (eid,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def _round_winner(eid, rnum):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
        "SELECT winner_team FROM event_round_results WHERE event_id = %s AND round_number = %s",
        (eid, rnum),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def _event_status(eid):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT status FROM event_master WHERE id = %s", (eid,))
    status = cur.fetchone()[0]
    cur.close()
    conn.close()
    return status


def test_parse_nonneg_int_accepts_zero_and_positive():
    assert parse_nonneg_int("0") == 0
    assert parse_nonneg_int(" 42 ") == 42


def test_parse_nonneg_int_rejects_bad_input():
    for bad in ["", "  ", "abc", "1.5", "-3", "5x", None]:
        assert parse_nonneg_int(bad) is None


def test_events_page_renders(client):
    response = client.get("/events")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_events_page_no_auth_required(client):
    response = client.get("/events", follow_redirects=False)
    assert response.status_code == 200


def test_events_page_shows_section_headers(client):
    response = client.get("/events")
    assert "Main Events" in response.text
    assert "Flong" in response.text
    assert "Friday Games" in response.text
    assert "Saturday Games" in response.text


# ── Winner submission (single events) ─────────────────────────────────────


def test_submit_winner_records_result(client, seeded_db):
    eid = _get_event_id("Escanaba")
    pid = _get_person_id("Mike Davis")
    resp = client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Red", "person_id": str(pid),
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert "error" not in resp.headers["location"]
    row = _result_row(eid)
    assert row is not None
    assert row[0] == 100   # Red is team_1 (id=1)
    assert row[1] == 0


def test_submit_winner_records_entered_by(client, seeded_db):
    eid = _get_event_id("Escanaba")
    pid = _get_person_id("Mike Davis")
    client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Red", "person_id": str(pid),
    })
    row = _result_row(eid)
    assert row[2] == "MikeD"


def test_submit_winner_rejects_invalid_team(client, seeded_db):
    eid = _get_event_id("Escanaba")
    pid = _get_person_id("Mike Davis")
    resp = client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Eagles", "person_id": str(pid),
    }, follow_redirects=False)
    assert "error=invalid_team" in resp.headers["location"]
    assert _result_row(eid) is None


def test_submit_winner_rejects_missing_person(client, seeded_db):
    eid = _get_event_id("Escanaba")
    resp = client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Red", "person_id": "",
    }, follow_redirects=False)
    assert "error=no_person" in resp.headers["location"]
    assert _result_row(eid) is None


def test_submit_winner_upserts_existing(client, seeded_db):
    eid = _get_event_id("Escanaba")
    pid = _get_person_id("Mike Davis")
    client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Red", "person_id": str(pid),
    })
    client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Blue", "person_id": str(pid),
    })
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM event_results WHERE event_id = %s", (eid,))
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()
    row = _result_row(eid)
    assert row[0] == 0     # Blue won → Red (team_1) has 0
    assert row[1] == 100


def test_submit_winner_marks_event_completed(client, seeded_db):
    eid = _get_event_id("Escanaba")
    pid = _get_person_id("Mike Davis")
    client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Red", "person_id": str(pid),
    })
    assert _event_status(eid) == "completed"


def test_winner_weekend_gate(client, seeded_db):
    _admin_conn_local = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = _admin_conn_local.cursor()
    cur.execute("UPDATE app_settings SET value = 'false' WHERE key = 'weekend_started'")
    _admin_conn_local.commit()
    cur.close()
    _admin_conn_local.close()

    eid = _get_event_id("Escanaba")
    pid = _get_person_id("Mike Davis")
    resp = client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Red", "person_id": str(pid),
    }, follow_redirects=False)
    assert "error=not_started" in resp.headers["location"]


# ── Round submission (best_of_3 events) ───────────────────────────────────


def test_submit_round_saves_winner(client, seeded_db):
    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    resp = client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Red", "person_id": str(pid),
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert "error" not in resp.headers["location"]
    assert _round_winner(eid, 1) == "Red"


def test_submit_round_sets_in_progress(client, seeded_db):
    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Red", "person_id": str(pid),
    })
    assert _event_status(eid) == "in_progress"


def test_submit_two_rounds_same_team_completes_event(client, seeded_db):
    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    for rnum in (1, 2):
        client.post("/events/round", data={
            "event_id": str(eid), "round_number": str(rnum),
            "winner_team": "Red", "person_id": str(pid),
        })
    assert _event_status(eid) == "completed"
    row = _result_row(eid)
    assert row is not None
    assert row[0] == 20  # Cornhole = 20 pts, Red is team_1
    assert row[1] == 0


def test_submit_split_rounds_stays_in_progress(client, seeded_db):
    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Red", "person_id": str(pid),
    })
    client.post("/events/round", data={
        "event_id": str(eid), "round_number": "2",
        "winner_team": "Blue", "person_id": str(pid),
    })
    assert _event_status(eid) == "in_progress"
    assert _result_row(eid) is None


def test_submit_round_3_decides_winner(client, seeded_db):
    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Red", "person_id": str(pid),
    })
    client.post("/events/round", data={
        "event_id": str(eid), "round_number": "2",
        "winner_team": "Blue", "person_id": str(pid),
    })
    client.post("/events/round", data={
        "event_id": str(eid), "round_number": "3",
        "winner_team": "Red", "person_id": str(pid),
    })
    assert _event_status(eid) == "completed"
    row = _result_row(eid)
    assert row[0] == 20   # Red wins
    assert row[1] == 0


def test_submit_round_upserts_existing(client, seeded_db):
    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Red", "person_id": str(pid),
    })
    client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Blue", "person_id": str(pid),
    })
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM event_round_results WHERE event_id = %s AND round_number = 1",
        (eid,),
    )
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()
    assert _round_winner(eid, 1) == "Blue"


def test_submit_round_rejects_missing_person(client, seeded_db):
    eid = _get_event_id("Cornhole")
    resp = client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Red", "person_id": "",
    }, follow_redirects=False)
    assert "error=no_person" in resp.headers["location"]


def test_submit_round_rejects_invalid_team(client, seeded_db):
    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    resp = client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Eagles", "person_id": str(pid),
    }, follow_redirects=False)
    assert "error=invalid_team" in resp.headers["location"]


def test_round_weekend_gate(client, seeded_db):
    _admin_conn_local = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = _admin_conn_local.cursor()
    cur.execute("UPDATE app_settings SET value = 'false' WHERE key = 'weekend_started'")
    _admin_conn_local.commit()
    cur.close()
    _admin_conn_local.close()

    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    resp = client.post("/events/round", data={
        "event_id": str(eid), "round_number": "1",
        "winner_team": "Red", "person_id": str(pid),
    }, follow_redirects=False)
    assert "error=not_started" in resp.headers["location"]


# ── Reset ──────────────────────────────────────────────────────────────────


def test_reset_clears_single_event(client, seeded_db):
    eid = _get_event_id("Escanaba")
    pid = _get_person_id("Mike Davis")
    client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Red", "person_id": str(pid),
    })
    assert _event_status(eid) == "completed"
    resp = client.post("/events/reset", data={
        "event_id": str(eid), "person_id": str(pid),
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert _result_row(eid) is None
    assert _event_status(eid) == "pending"


def test_reset_clears_rounds_and_result(client, seeded_db):
    eid = _get_event_id("Cornhole")
    pid = _get_person_id("Mike Davis")
    for rnum in (1, 2):
        client.post("/events/round", data={
            "event_id": str(eid), "round_number": str(rnum),
            "winner_team": "Red", "person_id": str(pid),
        })
    assert _event_status(eid) == "completed"
    client.post("/events/reset", data={
        "event_id": str(eid), "person_id": str(pid),
    })
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM event_round_results WHERE event_id = %s", (eid,))
    assert cur.fetchone()[0] == 0
    cur.close()
    conn.close()
    assert _result_row(eid) is None
    assert _event_status(eid) == "pending"


def test_reset_weekend_gate(client, seeded_db):
    _admin_conn_local = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = _admin_conn_local.cursor()
    cur.execute("UPDATE app_settings SET value = 'false' WHERE key = 'weekend_started'")
    _admin_conn_local.commit()
    cur.close()
    _admin_conn_local.close()

    eid = _get_event_id("Escanaba")
    pid = _get_person_id("Mike Davis")
    resp = client.post("/events/reset", data={
        "event_id": str(eid), "person_id": str(pid),
    }, follow_redirects=False)
    assert "error=not_started" in resp.headers["location"]


def test_reset_rejects_missing_person(client, seeded_db):
    eid = _get_event_id("Escanaba")
    resp = client.post("/events/reset", data={
        "event_id": str(eid), "person_id": "",
    }, follow_redirects=False)
    assert "error=no_person" in resp.headers["location"]
