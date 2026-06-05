from fastapi.testclient import TestClient
from backend.app.main import app


def test_analyst_valid_request(monkeypatch):
    async def fake_analyze_market(analyst_input):
        from backend.app.services.ai_analyst import AnalystOutput

        return AnalystOutput(
            ticker="AAPL",
            summary="The Venus-Jupiter cycle shows strong bullish signals.",
            cycle_explanation="Composite cycle is in positive territory with momentum increasing.",
            turning_points_explanation="Recent bottom at $150 confirms cycle reversal.",
            scan_explanation="Venus-Jupiter combination shows 0.63 correlation with market.",
            outlook="Expect upside continuation through June 2026.",
        )

    monkeypatch.setattr("backend.app.api.analyst.analyze_market", fake_analyze_market)

    client = TestClient(app)
    request_body = {
        "ticker": "AAPL",
        "composite_cycle_data": [
            {"date": "2026-05-18", "value": 0.5},
            {"date": "2026-05-19", "value": 0.6},
            {"date": "2026-05-20", "value": 0.65},
        ],
        "turning_points": [
            {"date": "2026-05-18", "type": "BOTTOM", "strength": 88},
            {"date": "2026-05-25", "type": "TOP", "strength": 82},
        ],
        "scanner_results": [
            {
                "cycle": "Venus-Jupiter",
                "correlation": 0.63,
                "lag_days": 5,
                "accuracy": 0.68,
                "score": 0.654,
            }
        ],
    }

    response = client.post("/api/analyst", json=request_body)

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert "Venus-Jupiter" in data["summary"]
    assert "cycle" in data["cycle_explanation"].lower()
    assert "turning" in data["turning_points_explanation"].lower()


def test_analyst_missing_required_field():
    client = TestClient(app)
    request_body = {
        "ticker": "AAPL",
        # missing composite_cycle_data
        "turning_points": [
            {"date": "2026-05-18", "type": "BOTTOM", "strength": 88}
        ],
    }

    response = client.post("/api/analyst", json=request_body)

    assert response.status_code == 422


def test_analyst_missing_ticker():
    client = TestClient(app)
    request_body = {
        "composite_cycle_data": [{"date": "2026-05-18", "value": 0.5}],
        "turning_points": [{"date": "2026-05-18", "type": "BOTTOM", "strength": 88}],
    }

    response = client.post("/api/analyst", json=request_body)

    assert response.status_code == 422


def test_analyst_with_optional_scanner_results(monkeypatch):
    async def fake_analyze_market(analyst_input):
        from backend.app.services.ai_analyst import AnalystOutput

        assert len(analyst_input.scanner_results) == 0
        return AnalystOutput(
            ticker="BTC-USD",
            summary="Summary",
            cycle_explanation="Cycle",
            turning_points_explanation="TP",
            scan_explanation="Scan",
            outlook="Outlook",
        )

    monkeypatch.setattr("backend.app.api.analyst.analyze_market", fake_analyze_market)

    client = TestClient(app)
    request_body = {
        "ticker": "BTC-USD",
        "composite_cycle_data": [{"date": "2026-05-18", "value": 0.5}],
        "turning_points": [{"date": "2026-05-18", "type": "BOTTOM", "strength": 88}],
    }

    response = client.post("/api/analyst", json=request_body)

    assert response.status_code == 200


def test_analyst_api_error_handling(monkeypatch):
    async def fake_analyze_market(analyst_input):
        raise ValueError("OpenAI API key not configured")

    monkeypatch.setattr("backend.app.api.analyst.analyze_market", fake_analyze_market)

    client = TestClient(app)
    request_body = {
        "ticker": "AAPL",
        "composite_cycle_data": [{"date": "2026-05-18", "value": 0.5}],
        "turning_points": [{"date": "2026-05-18", "type": "BOTTOM", "strength": 88}],
    }

    response = client.post("/api/analyst", json=request_body)

    assert response.status_code == 400
    assert "API key" in response.json()["detail"]


def test_analyst_multiple_turning_points(monkeypatch):
    async def fake_analyze_market(analyst_input):
        from backend.app.services.ai_analyst import AnalystOutput

        assert len(analyst_input.turning_points) == 5
        return AnalystOutput(
            ticker="AAPL",
            summary="Summary with 5 turning points",
            cycle_explanation="Cycle",
            turning_points_explanation="TP",
            scan_explanation="Scan",
            outlook="Outlook",
        )

    monkeypatch.setattr("backend.app.api.analyst.analyze_market", fake_analyze_market)

    client = TestClient(app)
    request_body = {
        "ticker": "AAPL",
        "composite_cycle_data": [
            {"date": f"2026-05-{i:02d}", "value": 0.5} for i in range(1, 6)
        ],
        "turning_points": [
            {"date": f"2026-05-{i:02d}", "type": "BOTTOM" if i % 2 == 0 else "TOP", "strength": 85 + i}
            for i in range(1, 6)
        ],
    }

    response = client.post("/api/analyst", json=request_body)

    assert response.status_code == 200
    data = response.json()
    assert "5 turning points" in data["summary"]
