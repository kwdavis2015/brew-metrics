import os

import psycopg2

from app.forms import parse_nonneg_int


def _ids():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole Tournament'")
    eid = cur.fetchone()[0]
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()
    return eid, pid


def _result_count(eid):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM event_results WHERE event_id = %s", (eid,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


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


def test_events_page_fills_zero_for_unscored(client):
    response = client.get("/events")
    assert 'value="0"' in response.text


def test_submit_rejects_non_numeric_score(client, seeded_db):
    eid, pid = _ids()
    response = client.post("/events/score", data={
        "event_id": str(eid), "team_1_points": "abc", "team_2_points": "10",
        "person_id": str(pid),
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error=invalid_score" in response.headers["location"]
    assert _result_count(eid) == 0


def test_submit_rejects_empty_score(client, seeded_db):
    eid, pid = _ids()
    response = client.post("/events/score", data={
        "event_id": str(eid), "team_1_points": "", "team_2_points": "",
        "person_id": str(pid),
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error=invalid_score" in response.headers["location"]
    assert _result_count(eid) == 0


def test_submit_rejects_negative_score(client, seeded_db):
    eid, pid = _ids()
    response = client.post("/events/score", data={
        "event_id": str(eid), "team_1_points": "-5", "team_2_points": "10",
        "person_id": str(pid),
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error=invalid_score" in response.headers["location"]
    assert _result_count(eid) == 0


def test_submit_rejects_missing_person(client, seeded_db):
    eid, _ = _ids()
    response = client.post("/events/score", data={
        "event_id": str(eid), "team_1_points": "10", "team_2_points": "5",
        "person_id": "",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error=no_person" in response.headers["location"]
    assert _result_count(eid) == 0


def test_submit_accepts_zero_scores(client, seeded_db):
    eid, pid = _ids()
    response = client.post("/events/score", data={
        "event_id": str(eid), "team_1_points": "0", "team_2_points": "0",
        "person_id": str(pid),
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error" not in response.headers["location"]
    assert _result_count(eid) == 1


def test_events_page_no_auth_required(client):
    response = client.get("/events", follow_redirects=False)
    assert response.status_code == 200


def test_submit_event_score_records_entered_by(client, seeded_db):
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole Tournament'")
    eid = cur.fetchone()[0]
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = client.post("/events/score", data={
        "event_id": str(eid),
        "team_1_points": "75",
        "team_2_points": "25",
        "person_id": str(pid),
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT team_1_points, team_2_points, entered_by FROM event_results WHERE event_id = %s", (eid,))
    row = cur.fetchone()
    assert row[0] == 75
    assert row[1] == 25
    assert row[2] == "MikeD"
    cur.close()
    conn.close()


def test_submit_event_score_updates_existing(client, seeded_db):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole Tournament'")
    eid = cur.fetchone()[0]
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    client.post("/events/score", data={
        "event_id": str(eid), "team_1_points": "50", "team_2_points": "50", "person_id": str(pid),
    })
    client.post("/events/score", data={
        "event_id": str(eid), "team_1_points": "100", "team_2_points": "0", "person_id": str(pid),
    })

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM event_results WHERE event_id = %s", (eid,))
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT team_1_points FROM event_results WHERE event_id = %s", (eid,))
    assert cur.fetchone()[0] == 100
    cur.close()
    conn.close()
