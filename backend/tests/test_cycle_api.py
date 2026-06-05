from datetime import date
from fastapi.testclient import TestClient
from backend.app.main import app


def test_read_cycle_valid(monkeypatch):
    async def fake_calculate_cycle(session, planet_a, planet_b, start_date, end_date):
        return [
            {"date": "2025-01-01", "value": 0.45},
            {"date": "2025-01-02", "value": 0.67},
        ]

    monkeypatch.setattr("backend.app.api.cycle.calculate_cycle", fake_calculate_cycle)
    client = TestClient(app)
    response = client.get("/api/cycle?planet_a=Sun&planet_b=Moon&start_date=2025-01-01&end_date=2025-01-02")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["date"] == "2025-01-01"
    assert payload[0]["value"] == 0.45


def test_read_cycle_invalid_planet(monkeypatch):
    async def fake_calculate_cycle(session, planet_a, planet_b, start_date, end_date):
        raise ValueError("Invalid planet. Must be one of: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn")

    monkeypatch.setattr("backend.app.api.cycle.calculate_cycle", fake_calculate_cycle)
    client = TestClient(app)
    response = client.get("/api/cycle?planet_a=InvalidPlanet&planet_b=Moon&start_date=2025-01-01&end_date=2025-01-02")

    assert response.status_code == 400


def test_read_cycle_not_found(monkeypatch):
    async def fake_calculate_cycle(session, planet_a, planet_b, start_date, end_date):
        return []

    monkeypatch.setattr("backend.app.api.cycle.calculate_cycle", fake_calculate_cycle)
    client = TestClient(app)
    response = client.get("/api/cycle?planet_a=Sun&planet_b=Moon&start_date=2025-01-01&end_date=2025-01-02")

    assert response.status_code == 404
    assert "No cycle data available" in response.json()["detail"]
