import pytest
from datetime import date
from backend.app.services.ai_analyst import (
    AnalystInput,
    AnalystOutput,
    format_analyst_prompt,
    parse_analysis_response,
)


def test_analyst_input_initialization():
    composite_data = [{"date": "2026-05-18", "value": 0.5}]
    turning_points = [{"date": "2026-05-18", "type": "BOTTOM", "strength": 88}]
    scanner_results = [
        {
            "cycle": "Venus-Jupiter",
            "correlation": 0.63,
            "lag_days": 5,
            "accuracy": 0.68,
            "score": 0.654,
        }
    ]

    analyst_input = AnalystInput(
        ticker="AAPL",
        composite_cycle_data=composite_data,
        turning_points=turning_points,
        scanner_results=scanner_results,
    )

    assert analyst_input.ticker == "AAPL"
    assert len(analyst_input.composite_cycle_data) == 1
    assert len(analyst_input.turning_points) == 1
    assert len(analyst_input.scanner_results) == 1


def test_analyst_output_initialization():
    output = AnalystOutput(
        ticker="AAPL",
        summary="The market is at a key turning point.",
        cycle_explanation="Venus-Jupiter cycle is in a positive phase.",
        turning_points_explanation="Major bottom detected at $150.",
        scan_explanation="Venus-Jupiter shows strongest correlation.",
        outlook="Expect upside over next 30 days.",
    )

    assert output.ticker == "AAPL"
    assert "key turning point" in output.summary


def test_analyst_output_to_dict():
    output = AnalystOutput(
        ticker="BTC-USD",
        summary="Test summary",
        cycle_explanation="Test cycle",
        turning_points_explanation="Test turning points",
        scan_explanation="Test scan",
        outlook="Test outlook",
    )

    data = output.to_dict()
    assert data["ticker"] == "BTC-USD"
    assert "summary" in data
    assert "cycle_explanation" in data
    assert "turning_points_explanation" in data
    assert "scan_explanation" in data
    assert "outlook" in data


def test_format_analyst_prompt_with_data():
    composite_data = [
        {"date": f"2026-05-{10+i:02d}", "value": 0.1 * i} for i in range(5)
    ]
    turning_points = [
        {"date": "2026-05-18", "type": "BOTTOM", "strength": 88},
        {"date": "2026-05-25", "type": "TOP", "strength": 82},
    ]
    scanner_results = [
        {
            "cycle": "Venus-Jupiter",
            "correlation": 0.63,
            "lag_days": 5,
            "accuracy": 0.68,
            "score": 0.654,
        },
        {
            "cycle": "Moon-Venus",
            "correlation": 0.58,
            "lag_days": 3,
            "accuracy": 0.62,
            "score": 0.608,
        },
    ]

    analyst_input = AnalystInput(
        ticker="AAPL",
        composite_cycle_data=composite_data,
        turning_points=turning_points,
        scanner_results=scanner_results,
    )

    prompt = format_analyst_prompt(analyst_input)

    assert "AAPL" in prompt
    assert "Venus-Jupiter" in prompt
    assert "Moon-Venus" in prompt
    assert "BOTTOM" in prompt
    assert "TOP" in prompt


def test_format_analyst_prompt_empty_data():
    analyst_input = AnalystInput(
        ticker="^JKSE",
        composite_cycle_data=[],
        turning_points=[],
        scanner_results=[],
    )

    prompt = format_analyst_prompt(analyst_input)

    assert "^JKSE" in prompt
    assert "No turning points" in prompt
    assert "No scan results" in prompt


def test_parse_analysis_response_valid():
    response_text = """
**Summary**: The market shows strong bullish signals.

**Cycle Explanation**: Venus-Jupiter cycle is in positive phase, suggesting upside momentum.

**Turning Points**: Major bottom detected, confirming bullish reversal.

**Scanner Insights**: Venus-Jupiter shows highest correlation with market direction.

**Outlook**: Expect continued upside through end of May.
"""

    parsed = parse_analysis_response(response_text)

    assert "summary" in parsed
    assert "cycle" in parsed["cycle_explanation"].lower()
    assert "bullish" in parsed["summary"].lower()


def test_parse_analysis_response_minimal():
    response_text = "Brief analysis without structured sections"

    parsed = parse_analysis_response(response_text)

    assert isinstance(parsed, dict)
    assert "summary" in parsed
