from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.schemas.prediction import ModelWeightResponse, PerformanceResponse, PredictionResponse, WatchlistResponse
from backend.app.services.prediction_engine import build_performance_report, build_prediction, build_watchlist, train_weight_profile

router = APIRouter(tags=["predictions"])


@router.get("/predictions/{ticker}", response_model=PredictionResponse)
async def read_prediction(
    ticker: str,
    horizon_days: int = Query(default=30, ge=5, le=120),
    account_equity: float = Query(default=10000, gt=0),
    risk_pct: float = Query(default=1.0, gt=0, le=10),
    session: AsyncSession = Depends(get_session),
) -> PredictionResponse:
    try:
        prediction = await build_prediction(session, ticker, horizon_days, account_equity, risk_pct)
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


@router.post("/model-weights/{ticker}/train", response_model=ModelWeightResponse)
async def train_model_weights(
    ticker: str,
    horizon_days: int = Query(default=30, ge=5, le=120),
    session: AsyncSession = Depends(get_session),
) -> ModelWeightResponse:
    try:
        profile = await train_weight_profile(session, ticker, horizon_days)
        return ModelWeightResponse(**profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal melatih bobot model: {exc}")


@router.get("/watchlist", response_model=WatchlistResponse)
async def read_watchlist(
    tickers: str = Query(default="AAPL,MSFT,NVDA,GOOGL,AMZN,META,TSLA"),
    horizon_days: int = Query(default=30, ge=5, le=120),
    session: AsyncSession = Depends(get_session),
) -> WatchlistResponse:
    try:
        report = await build_watchlist(session, tickers.split(","), horizon_days)
        return WatchlistResponse(**report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membaca watchlist: {exc}")
