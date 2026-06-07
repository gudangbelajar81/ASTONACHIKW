from datetime import date, datetime, time, timedelta, timezone
import json
import os
from urllib.parse import quote
from urllib.request import Request, urlopen
import pandas as pd


def _prepare_cache_environment() -> str:
    cache_dir = os.getenv("YFINANCE_CACHE_DIR", "/tmp/yfinance-cache")
    os.makedirs(cache_dir, exist_ok=True)
    os.environ.setdefault("YFINANCE_CACHE_DIR", cache_dir)
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp")
    os.environ.setdefault("HOME", "/tmp")
    return cache_dir


_prepare_cache_environment()

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import MarketPrice


def configure_yfinance_cache() -> None:
    cache_dir = _prepare_cache_environment()
    if hasattr(yf, "set_tz_cache_location"):
        yf.set_tz_cache_location(cache_dir)
    try:
        import yfinance.cache as yf_cache

        if hasattr(yf_cache, "set_cache_location"):
            yf_cache.set_cache_location(cache_dir)
        if hasattr(yf_cache, "get_tz_cache"):
            yf_cache.get_tz_cache().set_location(cache_dir)
        if hasattr(yf_cache, "get_cookie_cache"):
            yf_cache.get_cookie_cache().set_location(cache_dir)
    except Exception:
        pass


async def get_market_prices(session: AsyncSession, symbol: str) -> list[MarketPrice]:
    query = select(MarketPrice).where(MarketPrice.symbol == symbol).order_by(MarketPrice.date)
    result = await session.execute(query)
    return result.scalars().all()


def fetch_market_data(symbol: str, start: date, end: date) -> pd.DataFrame:
    configure_yfinance_cache()
    try:
        df = _fetch_yfinance_data(symbol, start, end)
    except Exception:
        df = _fetch_yahoo_chart_data(symbol, start, end)
    if df.empty:
        raise ValueError(f"No market data for {symbol}")
    return df[["date", "open", "high", "low", "close", "volume"]]


def _fetch_yfinance_data(symbol: str, start: date, end: date) -> pd.DataFrame:
    data = yf.download(
        symbol,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        progress=False,
        threads=False,
        auto_adjust=False,
    )
    if data.empty:
        raise ValueError(f"No market data for {symbol}")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.reset_index()
    data = data.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    data["date"] = pd.to_datetime(data["date"], utc=True).dt.date
    return data.dropna(subset=["close"])


def _fetch_yahoo_chart_data(symbol: str, start: date, end: date) -> pd.DataFrame:
    period1 = int(datetime.combine(start, time.min, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 AstroCycle/1.0"})
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise ValueError(f"No market data for {symbol}")

    timestamps = result.get("timestamp") or []
    quote_data = (result.get("indicators", {}).get("quote") or [{}])[0]
    rows = []
    for ts, open_, high, low, close, volume in zip(
        timestamps,
        quote_data.get("open") or [],
        quote_data.get("high") or [],
        quote_data.get("low") or [],
        quote_data.get("close") or [],
        quote_data.get("volume") or [],
    ):
        if close is None:
            continue
        rows.append(
            {
                "date": datetime.fromtimestamp(ts, timezone.utc).date(),
                "open": float(open_) if open_ is not None else float(close),
                "high": float(high) if high is not None else float(close),
                "low": float(low) if low is not None else float(close),
                "close": float(close),
                "volume": int(volume or 0),
            }
        )

    if not rows:
        raise ValueError(f"No market data for {symbol}")
    return pd.DataFrame(rows)
