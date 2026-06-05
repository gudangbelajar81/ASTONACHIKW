from fastapi.testclient import TestClient
from datetime import date
from backend.app.main import app


def test_read_turning_points_valid(monkeypatch):
    async def fake_detect_turning_points(session, ticker, combinations, lookback_days):
        from backend.app.services.turning_points_engine import TurningPoint
        return [
            TurningPoint(date(2026, 5, 18), "BOTTOM", 88),
            TurningPoint(date(2026, 5, 25), "TOP", 82),
            TurningPoint(date(2026, 6, 1), "BOTTOM", 85),
        ]

    monkeypatch.setattr(
        "backend.app.api.turning_points.detect_turning_points",
        fake_detect_turning_points,
    )
    client = TestClient(app)
    response = client.get("/api/turning-points?ticker=AAPL&lookback_days=90")

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["lookback_days"] == 90
    assert data["total_detected"] == 3
    assert len(data["turning_points"]) == 3
    assert data["turning_points"][0]["type"] == "BOTTOM"
    assert data["turning_points"][0]["strength"] == 88


def test_read_turning_points_default_lookback(monkeypatch):
    async def fake_detect_turning_points(session, ticker, combinations, lookback_days):
        from backend.app.services.turning_points_engine import TurningPoint
        assert lookback_days == 90
        return [TurningPoint(date(2026, 5, 18), "BOTTOM", 88)]

    monkeypatch.setattr(
        "backend.app.api.turning_points.detect_turning_points",
        fake_detect_turning_points,
    )
    client = TestClient(app)
    response = client.get("/api/turning-points?ticker=AAPL")

    assert response.status_code == 200
    data = response.json()
    assert data["lookback_days"] == 90


def test_read_turning_points_not_found(monkeypatch):
    async def fake_detect_turning_points(session, ticker, combinations, lookback_days):
        return []

    monkeypatch.setattr(
        "backend.app.api.turning_points.detect_turning_points",
        fake_detect_turning_points,
    )
    client = TestClient(app)
    response = client.get("/api/turning-points?ticker=AAPL&lookback_days=90")

    assert response.status_code == 404
    assert "No turning points detected" in response.json()["detail"]


def test_read_turning_points_invalid_lookback():
    client = TestClient(app)
    response = client.get("/api/turning-points?ticker=AAPL&lookback_days=400")

    assert response.status_code == 422


def test_read_turning_points_missing_ticker():
    client = TestClient(app)
    response = client.get("/api/turning-points")

    assert response.status_code == 422


def test_read_turning_points_error(monkeypatch):
    async def fake_detect_turning_points(session, ticker, combinations, lookback_days):
        raise ValueError("Market data fetch failed")

    monkeypatch.setattr(
        "backend.app.api.turning_points.detect_turning_points",
        fake_detect_turning_points,
    )
    client = TestClient(app)
    response = client.get("/api/turning-points?ticker=AAPL&lookback_days=90")

    assert response.status_code == 400
    assert "Market data fetch failed" in response.json()["detail"]
