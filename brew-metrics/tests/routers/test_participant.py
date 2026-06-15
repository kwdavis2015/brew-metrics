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


def test_keg_cap_blocks_at_330(client, seeded_db):
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

    response = client.post("/log-brew", data={"person_id": str(pid)})
    assert response.status_code == 200
    assert "330" in response.text
