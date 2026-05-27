from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_status_code():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_root_status_code():
    response = client.get("/")
    assert response.status_code == 200


def test_root_is_html():
    response = client.get("/")
    assert "text/html" in response.headers["content-type"]
