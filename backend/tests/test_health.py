from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/health")

    assert response.status_code == 200


def test_health_response_contract():
    response = client.get("/api/health")

    assert response.json() == {
        "status": "healthy",
        "service": "jobtrack-backend",
        "version": "0.1.0",
    }


def test_openapi_document_is_available():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "JobTrack API"
