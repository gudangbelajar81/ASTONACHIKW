from fastapi.testclient import TestClient
from backend.app.main import app


def test_read_planets_route(monkeypatch):
    async def fake_get_planetary_positions(session, target_date=None):
        return {
            "date": "2025-01-01",
            "sun": 123.45,
            "moon": 210.33,
            "mercury": 87.22,
            "venus": 98.23,
            "mars": 132.41,
            "jupiter": 212.11,
            "saturn": 45.19,
        }

    monkeypatch.setattr("backend.app.api.planets.get_planetary_positions", fake_get_planetary_positions)
    client = TestClient(app)
    response = client.get("/api/planets")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sun"] == 123.45
    assert payload["venus"] == 98.23
    assert payload["date"] == "2025-01-01"


def test_read_planets_route_not_found(monkeypatch):
    async def fake_get_planetary_positions(session, target_date=None):
        return None

    monkeypatch.setattr("backend.app.api.planets.get_planetary_positions", fake_get_planetary_positions)
    client = TestClient(app)
    response = client.get("/api/planets")

    assert response.status_code == 404
    assert response.json()["detail"] == "No planetary positions available for this date."
