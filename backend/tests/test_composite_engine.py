from datetime import date
import pytest
from backend.app.services.composite_engine import CycleCombination, apply_smoothing, project_future_values


def test_cycle_combination_valid():
    combo = CycleCombination("Sun", "Moon", 1.5)
    assert combo.planet_a == "Sun"
    assert combo.planet_b == "Moon"
    assert combo.weight == 1.5


def test_cycle_combination_invalid_planet():
    with pytest.raises(ValueError, match="Invalid planet"):
        CycleCombination("InvalidPlanet", "Moon", 1.0)


def test_cycle_combination_same_planet():
    with pytest.raises(ValueError, match="must be different"):
        CycleCombination("Sun", "Sun", 1.0)


def test_cycle_combination_invalid_weight():
    with pytest.raises(ValueError, match="Weight must be positive"):
        CycleCombination("Sun", "Moon", 0.0)


def test_apply_smoothing():
    data = [
        {"date": "2025-01-01", "value": 0.1},
        {"date": "2025-01-02", "value": 0.2},
        {"date": "2025-01-03", "value": 0.3},
        {"date": "2025-01-04", "value": 0.4},
        {"date": "2025-01-05", "value": 0.5},
    ]
    smoothed = apply_smoothing(data, 3)
    assert len(smoothed) == 5
    assert "smoothed" in smoothed[0]
    assert smoothed[0]["smoothed"] == pytest.approx(0.1, rel=0.01)
    assert smoothed[2]["smoothed"] == pytest.approx(0.2, rel=0.01)


def test_apply_smoothing_invalid_window():
    data = [{"date": "2025-01-01", "value": 0.1}]
    with pytest.raises(ValueError, match="Window must be positive"):
        apply_smoothing(data, 0)


def test_project_future_values():
    data = [
        {"date": "2025-01-01", "value": 0.1},
        {"date": "2025-01-02", "value": 0.2},
        {"date": "2025-01-03", "value": 0.3},
        {"date": "2025-01-04", "value": 0.4},
        {"date": "2025-01-05", "value": 0.5},
    ]
    projections = project_future_values(data, 3)
    assert len(projections) == 3
    assert all(-1.0 <= proj["value"] <= 1.0 for proj in projections)
    assert projections[0]["date"] == "2025-01-06"


def test_project_future_values_empty():
    projections = project_future_values([], 5)
    assert projections == []


def test_project_future_values_insufficient_data():
    data = [{"date": "2025-01-01", "value": 0.1}]
    projections = project_future_values(data, 5)
    assert projections == []
