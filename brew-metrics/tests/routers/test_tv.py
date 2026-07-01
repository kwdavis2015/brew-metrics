def test_tv_dashboard_renders(client):
    response = client.get("/tv")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_tv_has_auto_refresh(client):
    response = client.get("/tv")
    assert "hx-trigger" in response.text


def test_tv_has_no_nav(client):
    response = client.get("/tv")
    assert "main-nav" not in response.text


def test_tv_has_stat_band(client):
    response = client.get("/tv")
    assert "tv-statband" in response.text
    assert "Total Beers" in response.text


def test_tv_has_leaderboard_and_events_columns(client):
    response = client.get("/tv")
    assert "Leaderboard" in response.text
    assert "Events" in response.text
    assert response.text.count('data-tv-scroll>') == 2
