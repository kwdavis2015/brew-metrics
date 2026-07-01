import os

import psycopg2
import pytest


_BASE_DATA = {
    "full_name": "Test User",
    "expected_arrival_day": "Friday",
    "brew_drinking_level": "Hardened Veteran",
}

_FULL_DATA = {
    **_BASE_DATA,
    "nickname": "Testy",
    "expected_arrival_time": "3:00 PM",
    "skill_1": "Beer Chugging",
    "skill_2": "Keg Stand",
    "skill_3": "Trash Talk",
    "notes": "I will win",
    "beers_pledged": "30",
    "score_prediction_red": "500",
    "score_prediction_blue": "400",
    "first_to_puke": "Dave",
    "first_to_tap_out": "Steve",
}


def test_survey_form_renders(client):
    response = client.get("/survey")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_survey_shows_skills(client):
    response = client.get("/survey")
    assert "Cornhole Sniper" in response.text


def test_survey_shows_beer_levels(client):
    response = client.get("/survey")
    assert "Hardened Veteran" in response.text
    assert "Liver Donor Reject" in response.text


def test_survey_submit_redirects(client):
    response = client.post("/survey", data=_BASE_DATA, follow_redirects=False)
    assert response.status_code == 303


def test_survey_submitted_shows_confirmation(client):
    response = client.get("/survey?submitted=1")
    assert "liver" in response.text.lower()


def test_survey_creates_person(client):
    client.post("/survey", data=_BASE_DATA)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT full_name FROM people WHERE full_name = 'Test User'")
        row = cur.fetchone()
        assert row is not None
        cur.close()
    finally:
        conn.close()


def test_survey_saves_new_fields(client):
    client.post("/survey", data=_FULL_DATA)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT tsr.brew_drinking_level, tsr.beers_pledged,
                   tsr.score_prediction_red, tsr.score_prediction_blue,
                   tsr.first_to_puke, tsr.first_to_tap_out
            FROM team_survey_responses tsr
            JOIN people p ON tsr.person_id = p.id
            WHERE p.full_name = 'Test User'
        """)
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "Hardened Veteran"
        assert row[1] == 30
        assert row[2] == 500
        assert row[3] == 400
        assert row[4] == "Dave"
        assert row[5] == "Steve"
        cur.close()
    finally:
        conn.close()


def test_survey_resubmit_overwrites(client):
    client.post("/survey", data=_BASE_DATA)
    updated = {**_BASE_DATA, "brew_drinking_level": "Tourist"}
    client.post("/survey", data=updated)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT tsr.brew_drinking_level FROM team_survey_responses tsr
            JOIN people p ON tsr.person_id = p.id
            WHERE p.full_name = 'Test User'
        """)
        row = cur.fetchone()
        assert row[0] == "Tourist"
        cur.close()
    finally:
        conn.close()


def test_survey_export_is_csv_attachment(client):
    response = client.get("/survey/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]


def test_survey_export_includes_name_and_timestamp(client):
    client.post("/survey", data=_FULL_DATA)
    response = client.get("/survey/export")
    assert "full_name" in response.text          # header row
    assert "created_at" in response.text
    assert "Test User" in response.text          # full name
