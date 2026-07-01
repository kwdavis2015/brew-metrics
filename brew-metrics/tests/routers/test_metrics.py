import os

import psycopg2


def test_metrics_renders(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_metrics_export_is_csv_attachment(client):
    response = client.get("/metrics/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]


def test_metrics_export_has_header_row(client):
    response = client.get("/metrics/export")
    assert "created_at" in response.text
    assert "full_name" in response.text


def test_metrics_export_includes_full_name_and_timestamp(client, seeded_db):
    t1, _ = seeded_db
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM people WHERE full_name = 'Mike Davis'")
        pid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO brew_log (person_id, team_name, source) VALUES (%s, %s, 'keg')",
            (pid, t1),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()

    response = client.get("/metrics/export")
    # full name, not the "MikeD" nickname
    assert "Mike Davis" in response.text
    assert "MikeD" not in response.text
    # ISO date stamp from the brew timestamp
    assert "20" in response.text
