def test_dashboard_renders(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_dashboard_shows_teams(client):
    response = client.get("/dashboard")
    assert "Riks" in response.text
    assert "Wades" in response.text


def test_dashboard_shows_events(client):
    response = client.get("/dashboard")
    assert "Cornhole" in response.text


def test_brew_cup_scores_computed(client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    riks_pid = cur.fetchone()[0]
    cur.execute("SELECT id FROM people WHERE full_name = 'Steve Parker'")
    wades_pid = cur.fetchone()[0]
    for _ in range(10):
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, 'Riks', 'keg')",
            (riks_pid,),
        )
    for _ in range(5):
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, 'Wades', 'keg')",
            (wades_pid,),
        )
    conn.commit()
    cur.close()
    conn.close()

    response = client.get("/dashboard")
    assert "Brew Cup" in response.text
    assert "200" in response.text
    assert "100" in response.text
