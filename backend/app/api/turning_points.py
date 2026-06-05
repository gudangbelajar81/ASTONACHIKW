from fastapi import APIRouter, Query, HTTPException, Depends
from datetime import date as date_type
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session
from backend.app.schemas.turning_points import TurningPointsResponse, TurningPointResponse
from backend.app.services.turning_points_engine import detect_turning_points

router = APIRouter()


@router.get("/turning-points", response_model=TurningPointsResponse)
async def get_turning_points(
    ticker: str = Query(..., description="Market ticker (e.g., AAPL, ^JKSE)"),
    lookback_days: int = Query(90, ge=1, le=365, description="Days to analyze (1-365)"),
    session: AsyncSession = Depends(get_session),
) -> TurningPointsResponse:
    """
    Detect major turning points (tops and bottoms) in market cycles.

    Query parameters:
    - ticker: Market ticker (required)
    - lookback_days: Number of days to analyze (default 90, max 365)

    Returns:
    List of turning points with date, type (TOP/BOTTOM), and strength (0-100)
    """
    try:
        # Default composite combinations (can be extended with query params later)
        combinations = [
            {"planet_a": "Venus", "planet_b": "Jupiter", "weight": 1.0},
            {"planet_a": "Moon", "planet_b": "Saturn", "weight": 1.0},
            {"planet_a": "Mercury", "planet_b": "Mars", "weight": 0.8},
        ]

        turning_points = await detect_turning_points(
            session, ticker, combinations, lookback_days
        )

        if not turning_points:
            raise HTTPException(
                status_code=404,
                detail=f"No turning points detected for {ticker} in last {lookback_days} days",
            )

        response_points = [
            TurningPointResponse(
                date=tp.date,
                type=tp.type,
                strength=tp.strength,
            )
            for tp in turning_points
        ]

        return TurningPointsResponse(
            ticker=ticker,
            lookback_days=lookback_days,
            turning_points=response_points,
            total_detected=len(response_points),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting turning points: {str(e)}")
