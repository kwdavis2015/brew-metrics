import pytest


@pytest.fixture(autouse=True)
def _weekend_on(_admin_conn):
    """Brew logging requires weekend_started=true. Set it after _clean_db resets it."""
    cur = _admin_conn.cursor()
    cur.execute("UPDATE app_settings SET value = 'true' WHERE key = 'weekend_started'")
    cur.close()


def test_participant_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_participant_shows_active_people(client, seeded_db):
    response = client.get("/")
    assert "MikeD" in response.text
    assert "Alex Reed" not in response.text


def test_log_brew_post_returns_html(client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = client.post("/log-brew", data={"person_id": str(pid)})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_keg_logs_beyond_old_cap(client, seeded_db):
    """The 330 keg cap was removed; keg beers log freely past the old limit."""
    import os, psycopg2
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    for _ in range(330):
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, %s, 'keg')",
            (pid, t1),
        )
    conn.commit()
    cur.close()
    conn.close()

    response = client.post("/log-brew", data={"person_id": str(pid), "source": "keg"})
    assert response.status_code == 200

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM brew_log WHERE person_id = %s AND source = 'keg'", (pid,))
    assert cur.fetchone()[0] == 331
    cur.close()
    conn.close()


def test_byob_logs_successfully(client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = client.post("/log-brew", data={"person_id": str(pid), "source": "byob"})
    assert response.status_code == 200

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM brew_log WHERE person_id = %s AND source = 'byob'", (pid,))
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()
