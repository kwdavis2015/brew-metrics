def test_dashboard_renders(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_dashboard_shows_teams(client, seeded_db):
    t1, t2 = seeded_db
    response = client.get("/dashboard")
    assert t1 in response.text
    assert t2 in response.text


def test_dashboard_shows_events(client):
    response = client.get("/dashboard")
    assert "Escanaba" in response.text


def test_beers_drank_scores_computed(client, seeded_db):
    import os, psycopg2
    t1, t2 = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    p1 = cur.fetchone()[0]
    cur.execute("SELECT id FROM people WHERE full_name = 'Steve Parker'")
    p2 = cur.fetchone()[0]
    # 250 brews → 100 pts (250 * 0.4); 125 brews → 50 pts (125 * 0.4)
    for _ in range(250):
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, %s, 'keg')",
            (p1, t1),
        )
    for _ in range(125):
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, %s, 'keg')",
            (p2, t2),
        )
    conn.commit()
    cur.close()
    conn.close()

    response = client.get("/dashboard")
    assert "Beers Drank" in response.text
    assert "100" in response.text
    assert "50" in response.text
