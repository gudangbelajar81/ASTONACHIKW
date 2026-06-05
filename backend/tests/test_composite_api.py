import json
from fastapi.testclient import TestClient
from backend.app.main import app


def test_read_composite_valid(monkeypatch):
    async def fake_calculate_composite_cycle(session, combinations, start_date, end_date):
        return [
            {"date": "2025-01-01", "value": 0.45},
            {"date": "2025-01-02", "value": 0.55},
            {"date": "2025-01-03", "value": 0.65},
            {"date": "2025-01-04", "value": 0.75},
            {"date": "2025-01-05", "value": 0.85},
        ]

    monkeypatch.setattr("backend.app.api.composite.calculate_composite_cycle", fake_calculate_composite_cycle)

    client = TestClient(app)
    payload = {
        "combinations": [
            {"planet_a": "Sun", "planet_b": "Venus", "weight": 1.0},
            {"planet_a": "Sun", "planet_b": "Jupiter", "weight": 0.8},
            {"planet_a": "Moon", "planet_b": "Saturn", "weight": 0.5},
        ],
        "start_date": "2025-01-01",
        "end_date": "2025-01-05",
        "smoothing_windows": [7, 30, 60],
        "project_days": 0,
    }
    response = client.post("/api/composite", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["date"] == "2025-01-01"
    assert data[0]["value"] == 0.45
    assert "smoothed_7d" in data[0]


def test_read_composite_with_projection(monkeypatch):
    async def fake_calculate_composite_cycle(session, combinations, start_date, end_date):
        return [
            {"date": "2025-01-01", "value": 0.1},
            {"date": "2025-01-02", "value": 0.2},
            {"date": "2025-01-03", "value": 0.3},
            {"date": "2025-01-04", "value": 0.4},
            {"date": "2025-01-05", "value": 0.5},
        ]

    monkeypatch.setattr("backend.app.api.composite.calculate_composite_cycle", fake_calculate_composite_cycle)

    client = TestClient(app)
    payload = {
        "combinations": [
            {"planet_a": "Sun", "planet_b": "Venus", "weight": 1.0},
        ],
        "start_date": "2025-01-01",
        "end_date": "2025-01-05",
        "smoothing_windows": [7],
        "project_days": 3,
    }
    response = client.post("/api/composite", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 8
    projected = [item for item in data if item["projected"]]
    assert len(projected) == 3
    assert projected[0]["date"] == "2025-01-06"


def test_read_composite_invalid_date_format(monkeypatch):
    async def fake_calculate_composite_cycle(session, combinations, start_date, end_date):
        return []

    monkeypatch.setattr("backend.app.api.composite.calculate_composite_cycle", fake_calculate_composite_cycle)

    client = TestClient(app)
    payload = {
        "combinations": [
            {"planet_a": "Sun", "planet_b": "Venus", "weight": 1.0},
        ],
        "start_date": "01-01-2025",
        "end_date": "2025-01-05",
        "smoothing_windows": [7],
        "project_days": 0,
    }
    response = client.post("/api/composite", json=payload)

    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]


def test_read_composite_not_found(monkeypatch):
    async def fake_calculate_composite_cycle(session, combinations, start_date, end_date):
        return []

    monkeypatch.setattr("backend.app.api.composite.calculate_composite_cycle", fake_calculate_composite_cycle)

    client = TestClient(app)
    payload = {
        "combinations": [
            {"planet_a": "Sun", "planet_b": "Venus", "weight": 1.0},
        ],
        "start_date": "2025-01-01",
        "end_date": "2025-01-05",
        "smoothing_windows": [7],
        "project_days": 0,
    }
    response = client.post("/api/composite", json=payload)

    assert response.status_code == 404
    assert "No composite cycle data" in response.json()["detail"]
