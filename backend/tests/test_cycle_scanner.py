from datetime import date
import pytest
import numpy as np
from backend.app.services.cycle_scanner import (
    ScanResult,
    build_cycle_series,
    calculate_metrics,
)


def test_scan_result_score_calculation():
    result = ScanResult("Sun", "Venus", 0.6, 5, 0.65, 100)
    assert result.cycle == "Sun-Venus"
    assert result.correlation == 0.6
    assert result.lag_days == 5
    assert result.accuracy == 0.65
    expected_score = abs(0.6) * 0.6 + 0.65 * 0.4
    assert result.score == pytest.approx(expected_score)


def test_scan_result_to_dict():
    result = ScanResult("Moon", "Jupiter", 0.55, 3, 0.62, 150)
    data = result.to_dict()
    assert data["cycle"] == "Moon-Jupiter"
    assert "correlation" in data
    assert "lag_days" in data
    assert "accuracy" in data
    assert "score" in data
    assert "sample_count" in data


def test_build_cycle_series():
    measurements_by_date = {
        date(2025, 1, 1): {"Sun": 100, "Venus": 50},
        date(2025, 1, 2): {"Sun": 101, "Venus": 51},
        date(2025, 1, 3): {"Sun": 102, "Venus": 52},
    }
    cycle_data = build_cycle_series(
        measurements_by_date, "Sun", "Venus", date(2025, 1, 1), date(2025, 1, 3)
    )
    assert len(cycle_data) == 3
    assert "date" in cycle_data[0]
    assert "cycle" in cycle_data[0]
    assert -1 <= cycle_data[0]["cycle"] <= 1


def test_build_cycle_series_missing_data():
    measurements_by_date = {
        date(2025, 1, 1): {"Sun": 100},
        date(2025, 1, 3): {"Sun": 102, "Venus": 52},
    }
    cycle_data = build_cycle_series(
        measurements_by_date, "Sun", "Venus", date(2025, 1, 1), date(2025, 1, 3)
    )
    assert len(cycle_data) == 1


def test_calculate_metrics():
    cycle_data = [
        {"date": date(2025, 1, 1), "cycle": 0.5},
        {"date": date(2025, 1, 2), "cycle": 0.6},
        {"date": date(2025, 1, 3), "cycle": 0.7},
        {"date": date(2025, 1, 4), "cycle": 0.4},
        {"date": date(2025, 1, 5), "cycle": 0.3},
    ]
    market_data = [
        {"date": date(2025, 1, 1), "returns": 0.01, "direction": 1},
        {"date": date(2025, 1, 2), "returns": 0.02, "direction": 1},
        {"date": date(2025, 1, 3), "returns": -0.01, "direction": 0},
        {"date": date(2025, 1, 4), "returns": -0.02, "direction": 0},
        {"date": date(2025, 1, 5), "returns": 0.003, "direction": 1},
    ]
    correlation, lag_days, accuracy = calculate_metrics(cycle_data, market_data)
    assert isinstance(correlation, float)
    assert isinstance(lag_days, int)
    assert 0 <= accuracy <= 1


def test_calculate_metrics_insufficient_data():
    cycle_data = [{"date": date(2025, 1, 1), "cycle": 0.5}]
    market_data = [{"date": date(2025, 1, 1), "returns": 0.01, "direction": 1}]
    correlation, lag_days, accuracy = calculate_metrics(cycle_data, market_data)
    assert correlation == 0.0
    assert lag_days == 0
    assert accuracy == 0.5
