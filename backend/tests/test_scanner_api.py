from fastapi.testclient import TestClient
from backend.app.main import app


def test_read_scanner_valid(monkeypatch):
    async def fake_scan_cycles(session, ticker, lookback_years):
        return [
            {
                "cycle": "Venus-Jupiter",
                "correlation": 0.63,
                "lag_days": 5,
                "accuracy": 0.68,
                "score": 0.654,
                "sample_count": 1000,
            },
            {
                "cycle": "Moon-Venus",
                "correlation": 0.58,
                "lag_days": 3,
                "accuracy": 0.62,
                "score": 0.608,
                "sample_count": 1000,
            },
        ]

    monkeypatch.setattr("backend.app.api.scanner.scan_cycles", fake_scan_cycles)
    client = TestClient(app)
    response = client.get("/api/scanner?ticker=AAPL&lookback_years=3")

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["lookback_years"] == 3
    assert len(data["top_combinations"]) == 2
    assert data["top_combinations"][0]["cycle"] == "Venus-Jupiter"
    assert data["top_combinations"][0]["score"] == 0.654


def test_read_scanner_invalid_ticker(monkeypatch):
    async def fake_scan_cycles(session, ticker, lookback_years):
        raise ValueError(f"Insufficient market data for {ticker}")

    monkeypatch.setattr("backend.app.api.scanner.scan_cycles", fake_scan_cycles)
    client = TestClient(app)
    response = client.get("/api/scanner?ticker=INVALID&lookback_years=3")

    assert response.status_code == 400
    assert "Insufficient market data" in response.json()["detail"]


def test_read_scanner_invalid_lookback(monkeypatch):
    client = TestClient(app)
    response = client.get("/api/scanner?ticker=AAPL&lookback_years=25")

    assert response.status_code == 422


def test_read_scanner_not_found(monkeypatch):
    async def fake_scan_cycles(session, ticker, lookback_years):
        return []

    monkeypatch.setattr("backend.app.api.scanner.scan_cycles", fake_scan_cycles)
    client = TestClient(app)
    response = client.get("/api/scanner?ticker=AAPL&lookback_years=3")

    assert response.status_code == 404
    assert "No scan results" in response.json()["detail"]
