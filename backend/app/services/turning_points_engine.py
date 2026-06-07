from datetime import date, timedelta
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.composite_engine import calculate_composite_cycle, apply_smoothing
from backend.app.services.cycle_scanner import fetch_market_data


class TurningPoint:
    def __init__(self, turning_date: date, point_type: str, strength: int):
        self.date = turning_date
        self.type = point_type  # "TOP" or "BOTTOM"
        self.strength = strength

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": str(self.date),
            "type": self.type,
            "strength": self.strength,
        }


def detect_local_extrema(
    values: np.ndarray, window: int = 5
) -> List[tuple[int, str]]:
    """
    Detect local maxima and minima.

    Args:
        values: Array of cycle values
        window: Window size for local extrema detection (default 5)

    Returns:
        List of tuples (index, type) where type is "TOP" or "BOTTOM"
    """
    extrema = []

    for i in range(window, len(values) - window):
        left_window = values[i - window : i]
        right_window = values[i + 1 : i + window + 1]
        center = values[i]

        # Local maximum
        if center > np.max(left_window) and center > np.max(right_window):
            extrema.append((i, "TOP"))
        # Local minimum
        elif center < np.min(left_window) and center < np.min(right_window):
            extrema.append((i, "BOTTOM"))

    return extrema


def detect_cycle_reversals(values: np.ndarray, window: int = 5) -> List[tuple[int, str]]:
    """
    Detect composite cycle reversals (direction changes).

    Args:
        values: Array of cycle values
        window: Window size for smoothing before reversal detection

    Returns:
        List of tuples (index, type) where type is "TOP" or "BOTTOM"
    """
    reversals = []

    # Smooth the values slightly to filter noise
    smoothed = pd.Series(values).rolling(window=window, min_periods=1, center=True).mean()
    smoothed_values = smoothed.values

    # Detect sign changes (cycle crossing zero)
    for i in range(1, len(smoothed_values) - 1):
        prev_val = smoothed_values[i - 1]
        curr_val = smoothed_values[i]
        next_val = smoothed_values[i + 1]

        # Going from negative to positive (Bottom)
        if prev_val < 0 and curr_val <= 0 and next_val > 0:
            reversals.append((i, "BOTTOM"))
        # Going from positive to negative (Top)
        elif prev_val > 0 and curr_val >= 0 and next_val < 0:
            reversals.append((i, "TOP"))

    return reversals


def calculate_turning_point_strength(
    cycle_values: np.ndarray, market_values: np.ndarray, extrema_index: int
) -> int:
    """
    Calculate strength of a turning point (0-100).

    Strength based on:
    - Magnitude of cycle value
    - Market volatility at turning point
    - Consistency of local extrema (second derivative)

    Args:
        cycle_values: Array of composite cycle values
        market_values: Array of market returns
        extrema_index: Index of the extrema point

    Returns:
        Strength score 0-100
    """
    window = min(5, len(cycle_values) // 10)

    # Magnitude of cycle value (0-40 points)
    cycle_magnitude = abs(cycle_values[extrema_index]) * 40

    # Market volatility (0-30 points)
    if extrema_index > 0 and extrema_index < len(market_values):
        local_market = market_values[
            max(0, extrema_index - window) : min(len(market_values), extrema_index + window + 1)
        ]
        volatility = np.std(local_market) * 100 if len(local_market) > 1 else 0
        volatility_score = min(30, volatility * 30)
    else:
        volatility_score = 15

    # Consistency (0-30 points) - how pronounced is the local extrema
    if extrema_index > window and extrema_index < len(cycle_values) - window:
        left_vals = cycle_values[extrema_index - window : extrema_index]
        right_vals = cycle_values[extrema_index + 1 : extrema_index + window + 1]
        center = cycle_values[extrema_index]

        consistency = 0
        if center > 0:
            consistency = (
                (center - np.mean(left_vals)) + (center - np.mean(right_vals))
            ) / 2 * 15
        else:
            consistency = (
                (np.mean(left_vals) - center) + (np.mean(right_vals) - center)
            ) / 2 * 15

        consistency_score = min(30, max(0, consistency))
    else:
        consistency_score = 15

    total_strength = min(100, cycle_magnitude + volatility_score + consistency_score)
    return int(max(50, total_strength))


async def detect_turning_points(
    session: AsyncSession,
    ticker: str,
    combinations: List[Dict[str, Any]],
    lookback_days: int = 90,
) -> List[TurningPoint]:
    """
    Detect major turning points (tops and bottoms).

    Args:
        session: Database session
        ticker: Market ticker
        combinations: List of cycle combinations with weights
            [{"planet_a": "Venus", "planet_b": "Jupiter", "weight": 1.0}]
        lookback_days: Number of days to analyze (default 90)

    Returns:
        List of TurningPoint objects sorted by date
    """
    try:
        # Fetch market data
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)
        market_data = fetch_market_data(ticker, start_date, end_date)

        if not market_data:
            return []

        # Convert to DataFrame for easier manipulation
        market_df = pd.DataFrame(market_data)
        if market_df.empty:
            return []

        market_df["date"] = pd.to_datetime(market_df["date"])
        market_dates = market_df["date"].dt.date.values
        market_returns = market_df["returns"].values

        # Calculate composite cycle
        from backend.app.services.composite_engine import CycleCombination

        cycle_combos = [
            CycleCombination(c["planet_a"], c["planet_b"], c.get("weight", 1.0))
            for c in combinations
        ]

        cycle_data = await calculate_composite_cycle(
            session, cycle_combos, start_date, end_date
        )

        if not cycle_data:
            return []

        # Extract cycle values
        cycle_dates = [d["date"] for d in cycle_data]
        cycle_values = np.array([d["value"] for d in cycle_data])

        # Apply smoothing for cleaner extrema detection
        smoothed_cycle = apply_smoothing(cycle_data, window=3)
        smoothed_values = np.array([d["smoothed_3d"] if "smoothed_3d" in d else d["value"] for d in smoothed_cycle])

        # Detect local extrema
        extrema = detect_local_extrema(smoothed_values, window=5)

        # Detect cycle reversals
        reversals = detect_cycle_reversals(smoothed_values, window=3)

        # Combine detections (avoid duplicates)
        all_detections = {}
        for idx, tp_type in extrema:
            all_detections[idx] = tp_type

        for idx, tp_type in reversals:
            if idx not in all_detections:
                all_detections[idx] = tp_type

        # Align market data with cycle data for strength calculation
        turning_points = []
        for idx, tp_type in sorted(all_detections.items()):
            if 0 <= idx < len(cycle_dates):
                tp_date = cycle_dates[idx]

                # Find corresponding market data index
                market_idx = None
                for m_idx, m_date in enumerate(market_dates):
                    if m_date == tp_date:
                        market_idx = m_idx
                        break

                # Calculate strength
                if market_idx is not None:
                    strength = calculate_turning_point_strength(
                        smoothed_values, market_returns, idx
                    )
                else:
                    strength = int(abs(smoothed_values[idx]) * 50 + 40)
                    strength = min(100, strength)

                turning_points.append(TurningPoint(tp_date, tp_type, strength))

        return turning_points

    except Exception as e:
        raise ValueError(f"Error detecting turning points: {str(e)}")
