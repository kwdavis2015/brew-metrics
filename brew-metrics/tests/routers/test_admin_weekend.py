import os

import psycopg2
import pytest


def _weekend_started() -> bool:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key = 'weekend_started'")
        return cur.fetchone()[0] == 'true'
    finally:
        conn.close()


def _kickoff(admin_client):
    admin_client.post("/admin/weekend/kickoff", data={"started": "true"})


# --- Auth guards ---

def test_weekend_page_requires_auth(client):
    r = client.get("/admin/weekend", follow_redirects=False)
    assert r.status_code == 303
    assert "/admin/login" in r.headers["location"]


def test_kickoff_post_requires_auth(client):
    r = client.post("/admin/weekend/kickoff", data={"started": "true"}, follow_redirects=False)
    assert r.status_code == 303
    assert "/admin/login" in r.headers["location"]


def test_reset_post_requires_auth(client):
    r = client.post("/admin/weekend/reset", follow_redirects=False)
    assert r.status_code == 303
    assert "/admin/login" in r.headers["location"]


# --- Kickoff toggle ---

def test_weekend_page_renders_not_started(admin_client):
    r = admin_client.get("/admin/weekend")
    assert r.status_code == 200
    assert "Not Started" in r.text


def test_kickoff_sets_flag_true(admin_client):
    admin_client.post("/admin/weekend/kickoff", data={"started": "true"}, follow_redirects=False)
    assert _weekend_started() is True


def test_kickoff_redirects_to_weekend_page(admin_client):
    r = admin_client.post("/admin/weekend/kickoff", data={"started": "true"}, follow_redirects=False)
    assert r.status_code == 303
    assert "/admin/weekend" in r.headers["location"]


def test_kickoff_can_be_reversed(admin_client):
    admin_client.post("/admin/weekend/kickoff", data={"started": "true"})
    admin_client.post("/admin/weekend/kickoff", data={"started": "false"})
    assert _weekend_started() is False


def test_weekend_page_shows_kicked_off_after_start(admin_client):
    _kickoff(admin_client)
    r = admin_client.get("/admin/weekend")
    assert "Kicked Off" in r.text


# --- Participant gate ---

def test_participant_get_shows_kickoff_banner_when_not_started(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "1000 Beers Kickoff" in r.text


def test_log_brew_blocked_when_not_started(client, seeded_db):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
        pid = cur.fetchone()[0]
    finally:
        conn.close()

    r = client.post("/log-brew", data={"person_id": str(pid), "source": "keg"})
    assert r.status_code == 200
    assert "1000 Beers Kickoff" in r.text

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM brew_log WHERE person_id = %s", (pid,))
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_log_brew_allowed_when_started(admin_client, client, seeded_db):
    _kickoff(admin_client)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
        pid = cur.fetchone()[0]
    finally:
        conn.close()

    client.post("/log-brew", data={"person_id": str(pid), "source": "keg"})

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM brew_log WHERE person_id = %s AND status = 'active'", (pid,))
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()


# --- Events gate ---

def test_events_get_shows_kickoff_banner_when_not_started(client):
    r = client.get("/events")
    assert r.status_code == 200
    assert "1000 Beers Kickoff" in r.text


def test_event_score_blocked_when_not_started(client, seeded_db):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole'")
        eid = cur.fetchone()[0]
        cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
        pid = cur.fetchone()[0]
    finally:
        conn.close()

    r = client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Riks", "person_id": str(pid),
    }, follow_redirects=False)
    assert r.status_code == 303
    assert "error=not_started" in r.headers["location"]

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM event_results WHERE event_id = %s", (eid,))
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_event_score_allowed_when_started(admin_client, client, seeded_db):
    _kickoff(admin_client)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM event_master WHERE name = 'Escanaba'")
        eid = cur.fetchone()[0]
        cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
        pid = cur.fetchone()[0]
    finally:
        conn.close()

    r = client.post("/events/winner", data={
        "event_id": str(eid), "winner_team": "Riks", "person_id": str(pid),
    }, follow_redirects=False)
    assert r.status_code == 303
    assert "error" not in r.headers.get("location", "")


# --- Data reset ---

def test_reset_truncates_brew_log(admin_client, seeded_db):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
        pid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, 'Riks', 'keg')", (pid,)
        )
        conn.commit()
    finally:
        conn.close()

    admin_client.post("/admin/weekend/reset")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM brew_log")
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_reset_resets_event_status_to_pending(admin_client):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("UPDATE event_master SET status = 'completed' WHERE name = 'Cornhole'")
        conn.commit()
    finally:
        conn.close()

    admin_client.post("/admin/weekend/reset")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM event_master WHERE name = 'Cornhole'")
        assert cur.fetchone()[0] == 'pending'
    finally:
        conn.close()


def test_reset_clears_keg_finished_at(admin_client):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("UPDATE team_keg_state SET finished_at = NOW() WHERE team_name = 'Riks'")
        conn.commit()
    finally:
        conn.close()

    admin_client.post("/admin/weekend/reset")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT finished_at FROM team_keg_state WHERE team_name = 'Riks'")
        assert cur.fetchone()[0] is None
    finally:
        conn.close()


def test_reset_resets_weekend_started_flag(admin_client):
    _kickoff(admin_client)
    assert _weekend_started() is True
    admin_client.post("/admin/weekend/reset")
    assert _weekend_started() is False


def test_reset_keeps_people(admin_client, seeded_db):
    admin_client.post("/admin/weekend/reset")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM people")
        assert cur.fetchone()[0] > 0
    finally:
        conn.close()


def test_reset_keeps_survey_responses(admin_client, seeded_db):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
        pid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO team_survey_responses (person_id, expected_arrival_day) VALUES (%s, 'Friday')",
            (pid,),
        )
        conn.commit()
    finally:
        conn.close()

    admin_client.post("/admin/weekend/reset")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM team_survey_responses")
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()


def test_reset_clears_event_round_results(admin_client):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole'")
        eid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO event_round_results (event_id, round_number, winner_team) "
            "VALUES (%s, 1, 'Riks')",
            (eid,),
        )
        conn.commit()
    finally:
        conn.close()

    admin_client.post("/admin/weekend/reset")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM event_round_results")
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_reset_redirects_to_weekend_page(admin_client):
    r = admin_client.post("/admin/weekend/reset", follow_redirects=False)
    assert r.status_code == 303
    assert "/admin/weekend" in r.headers["location"]
