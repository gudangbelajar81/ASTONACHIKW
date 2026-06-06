from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.schemas.bandarmology import OHLCVResponse
from backend.app.services.bandarmology_engine import build_ohlcv_report

router = APIRouter(tags=["ohlcv"])


@router.get("/ohlcv/{ticker}", response_model=OHLCVResponse)
async def read_ohlcv_report(
    ticker: str,
    lookback_days: int = Query(default=180, ge=60, le=720),
    session: AsyncSession = Depends(get_session),
) -> OHLCVResponse:
    try:
        report = await build_ohlcv_report(session, ticker, lookback_days)
        return OHLCVResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membaca OHLCV: {exc}")
