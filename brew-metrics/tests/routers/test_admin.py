def test_login_form_renders(client):
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_login_bad_creds_redirects_with_error(client):
    response = client.post("/admin/login", data={
        "username": "wrong",
        "password": "wrong",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error" in response.headers["location"]


def test_login_good_creds_sets_cookie(client):
    response = client.post("/admin/login", data={
        "username": "admin",
        "password": "admin",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/survey" in response.headers["location"]
    assert "brew_admin_token" in response.headers.get("set-cookie", "")


def test_admin_survey_requires_auth(client):
    response = client.get("/admin/survey", follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_admin_brews_requires_auth(client):
    response = client.get("/admin/brews", follow_redirects=False)
    assert response.status_code == 303


def test_admin_events_requires_auth(client):
    response = client.get("/admin/events", follow_redirects=False)
    assert response.status_code == 303


def test_admin_survey_renders_with_auth(admin_client):
    response = admin_client.get("/admin/survey")
    assert response.status_code == 200


def test_admin_brews_renders_with_auth(admin_client):
    response = admin_client.get("/admin/brews")
    assert response.status_code == 200


def test_admin_events_renders_with_auth(admin_client):
    response = admin_client.get("/admin/events")
    assert response.status_code == 200


def test_assign_team(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Alex Reed'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/survey/assign", data={
        "person_id": str(pid),
        "team_name": "Wades",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT team_name FROM people WHERE id = %s", (pid,))
    assert cur.fetchone()[0] == "Wades"
    cur.close()
    conn.close()


def test_finalize_teams(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("UPDATE people SET team_name = 'Riks' WHERE full_name = 'Alex Reed'")
    conn.commit()
    cur.close()
    conn.close()

    response = admin_client.post("/admin/survey/finalize", follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT status FROM people WHERE full_name = 'Alex Reed'")
    assert cur.fetchone()[0] == "active"
    cur.close()
    conn.close()


def test_save_event_score(admin_client):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole Tournament'")
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/events/score", data={
        "event_id": str(eid),
        "riks_points": "100",
        "wades_points": "50",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT riks_points, wades_points FROM event_results WHERE event_id = %s", (eid,))
    row = cur.fetchone()
    assert row == (100, 50)
    cur.execute("SELECT status FROM event_master WHERE id = %s", (eid,))
    assert cur.fetchone()[0] == "completed"
    cur.close()
    conn.close()


def test_add_person_manually(admin_client):
    import os, psycopg2
    response = admin_client.post("/admin/survey/add-person", data={
        "full_name": "Walk Up Guy",
        "nickname": "WUG",
        "team_name": "Riks",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT status, team_name FROM people WHERE full_name = 'Walk Up Guy'")
    row = cur.fetchone()
    assert row == ("active", "Riks")
    cur.close()
    conn.close()


def test_reverse_brew(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, 'Riks', 'keg') RETURNING id",
        (pid,),
    )
    entry_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    response = admin_client.post("/admin/brews/reverse", data={
        "entry_id": str(entry_id),
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT status FROM brew_log WHERE id = %s", (entry_id,))
    assert cur.fetchone()[0] == "reversed"
    cur.execute("SELECT count(*) FROM brew_log WHERE reversal_of_entry_id = %s", (entry_id,))
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()
