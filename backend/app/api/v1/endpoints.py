from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session
from backend.app.schemas.models import (
    ForecastResponse,
    MarketPriceRead,
    ScanResult,
    TurningPointRead,
)
from backend.app.services import market, discovery, engine

router = APIRouter()


@router.get("/market/{symbol}", response_model=list[MarketPriceRead])
async def read_market_history(symbol: str, session: AsyncSession = Depends(get_session)):
    prices = await market.get_market_prices(session, symbol)
    if not prices:
        raise HTTPException(status_code=404, detail="Symbol not found or no data available")
    return prices


@router.get("/scan/{symbol}", response_model=ScanResult)
async def scan_cycles(symbol: str, session: AsyncSession = Depends(get_session)):
    candidates = await discovery.scan_best_cycles(session, symbol)
    return ScanResult(symbol=symbol, candidates=candidates)


@router.get("/forecast/{symbol}", response_model=list[ForecastResponse])
async def forecast_composite(symbol: str, session: AsyncSession = Depends(get_session)):
    result = await engine.build_composite_forecast(session, symbol)
    return result


@router.get("/turning-points/{symbol}", response_model=TurningPointRead)
async def turning_points(symbol: str, session: AsyncSession = Depends(get_session)):
    points = await engine.detect_turning_points(session, symbol)
    if not points:
        raise HTTPException(status_code=404, detail="Unable to detect turning points")
    return points
