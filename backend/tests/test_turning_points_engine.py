from datetime import date
import pytest
import numpy as np
from backend.app.services.turning_points_engine import (
    detect_local_extrema,
    detect_cycle_reversals,
    calculate_turning_point_strength,
    TurningPoint,
)


def test_turning_point_initialization():
    tp = TurningPoint(date(2026, 5, 18), "BOTTOM", 88)
    assert tp.date == date(2026, 5, 18)
    assert tp.type == "BOTTOM"
    assert tp.strength == 88


def test_turning_point_to_dict():
    tp = TurningPoint(date(2026, 5, 18), "TOP", 92)
    data = tp.to_dict()
    assert data["date"] == "2026-05-18"
    assert data["type"] == "TOP"
    assert data["strength"] == 92


def test_detect_local_extrema_maxima():
    values = np.array([0.1, 0.3, 0.5, 0.7, 0.8, 0.7, 0.5, 0.3, 0.1])
    extrema = detect_local_extrema(values, window=2)
    assert any(idx == 4 and tp_type == "TOP" for idx, tp_type in extrema)


def test_detect_local_extrema_minima():
    values = np.array([0.7, 0.5, 0.3, 0.1, 0.0, 0.1, 0.3, 0.5, 0.7])
    extrema = detect_local_extrema(values, window=2)
    assert any(idx == 4 and tp_type == "BOTTOM" for idx, tp_type in extrema)


def test_detect_cycle_reversals_bottom():
    values = np.array([-0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5])
    reversals = detect_cycle_reversals(values, window=2)
    assert len(reversals) > 0
    assert any(tp_type == "BOTTOM" for _, tp_type in reversals)


def test_detect_cycle_reversals_top():
    values = np.array([0.5, 0.3, 0.1, 0.0, -0.1, -0.3, -0.5])
    reversals = detect_cycle_reversals(values, window=2)
    assert len(reversals) > 0
    assert any(tp_type == "TOP" for _, tp_type in reversals)


def test_calculate_turning_point_strength():
    cycle_values = np.array([0.1, 0.3, 0.5, 0.7, 0.8, 0.7, 0.5, 0.3, 0.1])
    market_values = np.array([0.01, 0.02, 0.015, 0.01, 0.005, 0.01, 0.015, 0.02, 0.01])
    strength = calculate_turning_point_strength(cycle_values, market_values, 4)
    assert 50 <= strength <= 100


def test_calculate_turning_point_strength_range():
    cycle_values = np.random.randn(100)
    market_values = np.random.randn(100) * 0.01
    strength = calculate_turning_point_strength(cycle_values, market_values, 50)
    assert 0 <= strength <= 100
    assert isinstance(strength, int)
