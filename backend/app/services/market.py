from datetime import date
import pandas as pd
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import MarketPrice


async def get_market_prices(session: AsyncSession, symbol: str) -> list[MarketPrice]:
    query = select(MarketPrice).where(MarketPrice.symbol == symbol).order_by(MarketPrice.date)
    result = await session.execute(query)
    return result.scalars().all()


def fetch_market_data(symbol: str, start: date, end: date) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start.isoformat(), end=(end.isoformat()), interval="1d")
    if df.empty:
        raise ValueError(f"No market data for {symbol}")
    df = df.reset_index()
    df = df.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    return df[["date", "open", "high", "low", "close", "volume"]]
