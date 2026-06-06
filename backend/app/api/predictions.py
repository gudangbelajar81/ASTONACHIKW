from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.schemas.prediction import PerformanceResponse, PredictionResponse
from backend.app.services.prediction_engine import build_performance_report, build_prediction

router = APIRouter(tags=["predictions"])


@router.get("/predictions/{ticker}", response_model=PredictionResponse)
async def read_prediction(
    ticker: str,
    horizon_days: int = Query(default=30, ge=5, le=120),
    session: AsyncSession = Depends(get_session),
) -> PredictionResponse:
    try:
        prediction = await build_prediction(session, ticker, horizon_days)
        return PredictionResponse(**prediction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membuat prediksi: {exc}")


@router.get("/performance/{ticker}", response_model=PerformanceResponse)
async def read_performance(
    ticker: str,
    horizon_days: int = Query(default=30, ge=5, le=120),
    session: AsyncSession = Depends(get_session),
) -> PerformanceResponse:
    try:
        report = await build_performance_report(session, ticker, horizon_days)
        return PerformanceResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membuat performance report: {exc}")
