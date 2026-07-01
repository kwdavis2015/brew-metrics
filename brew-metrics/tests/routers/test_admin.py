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


def test_login_page_redirects_when_authenticated(admin_client):
    response = admin_client.get("/admin/login", follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/survey" in response.headers["location"]


def test_session_refreshes_on_authenticated_request(admin_client):
    response = admin_client.get("/admin/survey")
    assert response.status_code == 200
    assert "brew_admin_token" in response.headers.get("set-cookie", "")


def test_no_session_refresh_without_valid_token(client):
    response = client.get("/admin/survey", follow_redirects=False)
    assert response.status_code == 303
    assert "brew_admin_token" not in response.headers.get("set-cookie", "")


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


def test_team_creation_route_removed(admin_client):
    response = admin_client.post("/admin/teams/create", data={"name": "Eagles"})
    assert response.status_code == 404


def test_admin_survey_shows_team_roster(admin_client):
    admin_client.post("/admin/survey/add-person", data={
        "full_name": "Roster Guy", "nickname": "RG", "team_name": "Red",
    })
    response = admin_client.get("/admin/survey")
    assert response.status_code == 200
    assert "Team Roster" in response.text
    assert "Roster Guy" in response.text


def test_assign_team(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Alex Reed'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/survey/assign", data={
        "person_id": str(pid),
        "team_name": t1,
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT team_name FROM people WHERE id = %s", (pid,))
    assert cur.fetchone()[0] == t1
    cur.close()
    conn.close()


def test_finalize_teams(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("UPDATE people SET team_name = %s WHERE full_name = 'Alex Reed'", (t1,))
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


def test_admin_save_event_winner(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Escanaba'")
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/events/winner", data={
        "event_id": str(eid),
        "winner_team": "Red",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT team_1_points, team_2_points FROM event_results WHERE event_id = %s", (eid,))
    row = cur.fetchone()
    assert row == (100, 0)
    cur.execute("SELECT status FROM event_master WHERE id = %s", (eid,))
    assert cur.fetchone()[0] == "completed"
    cur.close()
    conn.close()


def test_admin_save_event_winner_rejects_invalid_team(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Escanaba'")
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/events/winner", data={
        "event_id": str(eid),
        "winner_team": "Eagles",
    }, follow_redirects=False)
    assert "error=invalid_team" in response.headers["location"]

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM event_results WHERE event_id = %s", (eid,))
    assert cur.fetchone()[0] == 0
    cur.close()
    conn.close()


def test_admin_save_round_result(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole'")
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/events/round", data={
        "event_id": str(eid),
        "round_number": "1",
        "winner_team": "Blue",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
        "SELECT winner_team FROM event_round_results WHERE event_id = %s AND round_number = 1",
        (eid,),
    )
    assert cur.fetchone()[0] == "Blue"
    cur.close()
    conn.close()


def test_admin_reset_event(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Escanaba'")
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()

    admin_client.post("/admin/events/winner", data={"event_id": str(eid), "winner_team": "Red"})
    admin_client.post("/admin/events/reset", data={"event_id": str(eid)}, follow_redirects=False)

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM event_results WHERE event_id = %s", (eid,))
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT status FROM event_master WHERE id = %s", (eid,))
    assert cur.fetchone()[0] == "pending"
    cur.close()
    conn.close()


def test_admin_winner_requires_auth(client, seeded_db):
    response = client.post("/admin/events/winner", data={
        "event_id": "1", "winner_team": "Red",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_admin_round_requires_auth(client, seeded_db):
    response = client.post("/admin/events/round", data={
        "event_id": "1", "round_number": "1", "winner_team": "Red",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_admin_reset_requires_auth(client, seeded_db):
    response = client.post("/admin/events/reset", data={
        "event_id": "1",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_update_event_status(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole'")
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/events/status", data={
        "event_id": str(eid),
        "status": "in_progress",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT status FROM event_master WHERE id = %s", (eid,))
    assert cur.fetchone()[0] == "in_progress"
    cur.close()
    conn.close()


def test_update_event_status_overrides_completed(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole'")
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()

    # Scoring auto-completes the event...
    admin_client.post("/admin/events/winner", data={
        "event_id": str(eid), "winner_team": "Red",
    }, follow_redirects=False)
    # ...and the admin can override it back to in_progress.
    admin_client.post("/admin/events/status", data={
        "event_id": str(eid), "status": "in_progress",
    }, follow_redirects=False)

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT status FROM event_master WHERE id = %s", (eid,))
    assert cur.fetchone()[0] == "in_progress"
    cur.close()
    conn.close()


def test_update_event_status_rejects_invalid(admin_client, seeded_db):
    import os, psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM event_master WHERE name = 'Cornhole'")
    eid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/events/status", data={
        "event_id": str(eid),
        "status": "cancelled",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error=invalid_status" in response.headers["location"]

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT status FROM event_master WHERE id = %s", (eid,))
    assert cur.fetchone()[0] == "pending"
    cur.close()
    conn.close()


def test_update_event_status_requires_admin(client, seeded_db):
    response = client.post("/admin/events/status", data={
        "event_id": "1", "status": "in_progress",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_cheat_deduction_reduces_team_score(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    response = admin_client.post("/admin/events/deduct", data={
        "team_name": t1,
        "points": "25",
        "reason": "cheated at cornhole",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
        "SELECT amount FROM admin_adjustments WHERE team_name = %s AND adjustment_type = 'cheat_deduction'",
        (t1,),
    )
    assert cur.fetchone()[0] == -25
    cur.close()
    conn.close()


def test_cheat_deduction_requires_reason(admin_client, seeded_db):
    t1, _ = seeded_db
    response = admin_client.post("/admin/events/deduct", data={
        "team_name": t1, "points": "10", "reason": "  ",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error=missing_reason" in response.headers["location"]


def test_cheat_deduction_rejects_zero_points(admin_client, seeded_db):
    t1, _ = seeded_db
    response = admin_client.post("/admin/events/deduct", data={
        "team_name": t1, "points": "0", "reason": "cheating",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "error=invalid_deduction" in response.headers["location"]


def test_cheat_deduction_requires_admin(client, seeded_db):
    t1, _ = seeded_db
    response = client.post("/admin/events/deduct", data={
        "team_name": t1, "points": "10", "reason": "cheating",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_add_person_manually(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    response = admin_client.post("/admin/survey/add-person", data={
        "full_name": "Walk Up Guy",
        "nickname": "WUG",
        "team_name": t1,
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT status, team_name FROM people WHERE full_name = 'Walk Up Guy'")
    row = cur.fetchone()
    assert row == ("active", t1)
    cur.close()
    conn.close()


def test_delete_person_purges_all_data(admin_client, seeded_db):
    import os, psycopg2
    # Full survey submission populates people + survey rows.
    admin_client.post("/survey", data={
        "full_name": "Test Bot",
        "expected_arrival_day": "Friday",
    })
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Test Bot'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/survey/delete-person", data={
        "person_id": str(pid),
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM people WHERE id = %s", (pid,))
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT count(*) FROM team_survey_responses WHERE person_id = %s", (pid,))
    assert cur.fetchone()[0] == 0
    cur.close()
    conn.close()


def test_delete_person_purges_brews_and_reversals(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, %s, 'keg') RETURNING id",
        (pid, t1),
    )
    entry_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    # Create a reversal row (self-referencing brew_log) before deleting.
    admin_client.post("/admin/brews/reverse", data={"entry_id": str(entry_id)})

    response = admin_client.post("/admin/survey/delete-person", data={
        "person_id": str(pid),
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM brew_log WHERE person_id = %s", (pid,))
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT count(*) FROM people WHERE id = %s", (pid,))
    assert cur.fetchone()[0] == 0
    cur.close()
    conn.close()


def test_delete_person_purges_admin_adjustments(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO admin_adjustments (adjustment_type, person_id, reason, entered_by) "
        "VALUES ('manual', %s, 'test', 'admin')",
        (pid,),
    )
    conn.commit()
    cur.close()
    conn.close()

    response = admin_client.post("/admin/survey/delete-person", data={
        "person_id": str(pid),
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM admin_adjustments WHERE person_id = %s", (pid,))
    assert cur.fetchone()[0] == 0
    cur.close()
    conn.close()


def test_delete_nonexistent_person_is_noop(admin_client, seeded_db):
    response = admin_client.post("/admin/survey/delete-person", data={
        "person_id": "999999",
    }, follow_redirects=False)
    assert response.status_code == 303


def test_delete_person_requires_auth(client, seeded_db):
    response = client.post("/admin/survey/delete-person", data={
        "person_id": "1",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_admin_add_brew(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/brews/add", data={
        "person_id": str(pid),
        "source": "keg",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM brew_log WHERE person_id = %s AND status = 'active'", (pid,))
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()


def test_admin_add_brew_byob(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.close()
    conn.close()

    response = admin_client.post("/admin/brews/add", data={
        "person_id": str(pid),
        "source": "byob",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT source FROM brew_log WHERE person_id = %s AND status = 'active'", (pid,))
    assert cur.fetchone()[0] == "byob"
    cur.close()
    conn.close()


def test_admin_add_brew_logs_beyond_old_cap(admin_client, seeded_db):
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

    response = admin_client.post("/admin/brews/add", data={
        "person_id": str(pid),
        "source": "keg",
    }, follow_redirects=False)
    assert response.status_code == 303

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM brew_log WHERE person_id = %s AND status = 'active'", (pid,))
    assert cur.fetchone()[0] == 331
    cur.close()
    conn.close()


def test_reverse_brew(admin_client, seeded_db):
    import os, psycopg2
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
    pid = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, %s, 'keg') RETURNING id",
        (pid, t1),
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
