"""
Seed script for market prices and ephemeris (astro_measurements).
Usage (from repo root):
    python -m backend.seeds.seed_data --symbol AAPL --days 365

This script requires network access (yfinance) and swisseph ephemeris files.
"""
import asyncio
from datetime import date, timedelta
import argparse
from sqlalchemy.dialects.postgresql import insert
from backend.app.db.session import AsyncSessionLocal
from backend.app.db.models import MarketPrice
from backend.app.services.market import fetch_market_data
from backend.app.services import ephemeris_service


async def seed_market(session, symbol: str, start_date: date, end_date: date):
    print(f"Fetching market data for {symbol} from {start_date} to {end_date}...")
    df = fetch_market_data(symbol, start_date, end_date)
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "date": row["date"].date(),
                "symbol": symbol,
                "close": float(row["close"]),
                "open": float(row["open"]) if not pd_isna(row["open"]) else None,
                "high": float(row["high"]) if not pd_isna(row["high"]) else None,
                "low": float(row["low"]) if not pd_isna(row["low"]) else None,
                "volume": float(row["volume"]) if not pd_isna(row["volume"]) else None,
            }
        )

    if not rows:
        print("No market rows to insert")
        return

    stmt = insert(MarketPrice)
    stmt = stmt.on_conflict_do_update(
        index_elements=["date", "symbol"],
        set_={
            "close": stmt.excluded.close,
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "volume": stmt.excluded.volume,
        },
    )
    await session.execute(stmt, rows)
    await session.commit()
    print(f"Inserted/updated {len(rows)} market rows for {symbol}")


def pd_isna(val):
    try:
        import pandas as pd
        return pd.isna(val)
    except Exception:
        return val is None


async def seed_ephemeris(session, start_date: date, end_date: date):
    print(f"Seeding ephemeris from {start_date} to {end_date}...")
    await ephemeris_service.upsert_planetary_positions(session, start_date, end_date)
    print("Ephemeris data seeded")


async def main(symbol: str, days: int):
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    async with AsyncSessionLocal() as session:
        # Seed market
        try:
            await seed_market(session, symbol, start_date, end_date)
        except Exception as e:
            print(f"Market seed failed: {e}")

        # Seed ephemeris
        try:
            await seed_ephemeris(session, start_date, end_date)
        except Exception as e:
            print(f"Ephemeris seed failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="AAPL", help="Market ticker to fetch (default AAPL)")
    parser.add_argument("--days", type=int, default=365, help="Days of history to seed (default 365)")
    args = parser.parse_args()

    asyncio.run(main(args.symbol, args.days))
