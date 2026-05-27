def test_survey_form_renders(client):
    response = client.get("/survey")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_survey_shows_skills(client):
    response = client.get("/survey")
    assert "cornhole" in response.text


def test_survey_submit_redirects(client):
    response = client.post("/survey", data={
        "full_name": "Test User",
        "expected_arrival_day": "Friday",
        "brew_drinking_skill_rank": "2",
    }, follow_redirects=False)
    assert response.status_code == 303


def test_survey_submitted_shows_confirmation(client):
    response = client.get("/survey?submitted=1")
    assert "submitted" in response.text.lower()


def test_survey_creates_person(client):
    client.post("/survey", data={
        "full_name": "New Person",
        "nickname": "Newbie",
        "expected_arrival_day": "Thursday",
        "brew_drinking_skill_rank": "3",
    })
    response = client.get("/admin/login")
    assert response.status_code == 200
