def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except Exception:
        return fallback


def score_0_100(value: float) -> int:
    return int(round(clamp(value) * 100))
