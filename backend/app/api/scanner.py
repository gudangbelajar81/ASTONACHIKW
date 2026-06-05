from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session
from backend.app.services.cycle_scanner import scan_cycles

router = APIRouter(tags=["scanner"])


@router.get("/scanner")
async def read_scanner(
    ticker: str = Query(..., description="Market ticker (e.g., AAPL, ^JKSE, BTC-USD)"),
    lookback_years: int = Query(3, ge=1, le=20, description="Number of years to lookback"),
    session: AsyncSession = Depends(get_session),
):
    try:
        results = await scan_cycles(session, ticker, lookback_years)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Scanner processing failed")

    if not results:
        raise HTTPException(status_code=404, detail="No scan results available")

    return {
        "ticker": ticker,
        "lookback_years": lookback_years,
        "combinations_tested": 21,
        "top_combinations": results,
    }
