import pandas as pd

from backend.app.services.technical.common import safe_float


def moving_average(close: pd.Series, period: int) -> float:
    return safe_float(close.rolling(period, min_periods=max(3, period // 4)).mean().iloc[-1], safe_float(close.iloc[-1]))


def rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, 0.000001)
    return safe_float(100 - (100 / (1 + rs.iloc[-1])), 50.0)


def macd(close: pd.Series) -> dict:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    line = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    histogram = line - signal
    previous_hist = safe_float(histogram.iloc[-2]) if len(histogram) > 1 else 0.0
    current_hist = safe_float(histogram.iloc[-1])
    return {
        "line": safe_float(line.iloc[-1]),
        "signal": safe_float(signal.iloc[-1]),
        "histogram": current_hist,
        "crossing_up": previous_hist <= 0 < current_hist,
    }


def atr(df: pd.DataFrame, period: int = 14) -> float:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    true_range = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    return safe_float(true_range.rolling(period, min_periods=period).mean().iloc[-1], safe_float(high.iloc[-1] - low.iloc[-1]))


def stochastic(df: pd.DataFrame, period: int = 14) -> float:
    high = df["high"].astype(float).rolling(period, min_periods=period).max()
    low = df["low"].astype(float).rolling(period, min_periods=period).min()
    close = df["close"].astype(float)
    return safe_float(((close.iloc[-1] - low.iloc[-1]) / max(high.iloc[-1] - low.iloc[-1], 0.000001)) * 100, 50.0)


def adx(df: pd.DataFrame, period: int = 14) -> float:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    plus_dm = (high.diff()).where((high.diff() > -low.diff()) & (high.diff() > 0), 0.0)
    minus_dm = (-low.diff()).where((-low.diff() > high.diff()) & (-low.diff() > 0), 0.0)
    true_range = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr_series = true_range.rolling(period, min_periods=period).mean().replace(0, 0.000001)
    plus_di = 100 * plus_dm.rolling(period, min_periods=period).mean() / atr_series
    minus_di = 100 * minus_dm.rolling(period, min_periods=period).mean() / atr_series
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 0.000001)) * 100
    return safe_float(dx.rolling(period, min_periods=period).mean().iloc[-1], 15.0)


def roc(close: pd.Series, period: int = 12) -> float:
    if len(close) <= period:
        return 0.0
    previous = safe_float(close.iloc[-period - 1], safe_float(close.iloc[-1]))
    return safe_float(close.iloc[-1]) / previous - 1 if previous > 0 else 0.0


def bollinger_position(close: pd.Series, period: int = 20) -> dict:
    middle = close.rolling(period, min_periods=period).mean()
    std = close.rolling(period, min_periods=period).std()
    upper = middle + std * 2
    lower = middle - std * 2
    latest = safe_float(close.iloc[-1])
    width = max(safe_float(upper.iloc[-1] - lower.iloc[-1]), 0.000001)
    position = (latest - safe_float(lower.iloc[-1], latest)) / width
    return {"position": position, "upper": safe_float(upper.iloc[-1]), "middle": safe_float(middle.iloc[-1]), "lower": safe_float(lower.iloc[-1])}


def vwap(df: pd.DataFrame, window: int = 20) -> float:
    recent = df.tail(window)
    typical = (recent["high"].astype(float) + recent["low"].astype(float) + recent["close"].astype(float)) / 3
    volume = recent["volume"].astype(float)
    total_volume = safe_float(volume.sum())
    return safe_float((typical * volume).sum() / total_volume, safe_float(recent["close"].iloc[-1])) if total_volume > 0 else safe_float(recent["close"].iloc[-1])


def ichimoku(df: pd.DataFrame) -> dict:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    tenkan = (safe_float(high.tail(9).max()) + safe_float(low.tail(9).min())) / 2
    kijun = (safe_float(high.tail(26).max()) + safe_float(low.tail(26).min())) / 2
    span_a = (tenkan + kijun) / 2
    span_b = (safe_float(high.tail(52).max()) + safe_float(low.tail(52).min())) / 2
    return {"tenkan": tenkan, "kijun": kijun, "span_a": span_a, "span_b": span_b}
