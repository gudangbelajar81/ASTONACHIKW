from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.schemas.backtest import (
    BacktestRequest, BacktestResponse,
    ScreenerRequest, ScreenerResponse,
    SetupBacktestRequest, SetupBacktestResponse,
)
from backend.app.schemas.prediction import ModelWeightResponse, PerformanceResponse, PredictionResponse, WatchlistResponse
from backend.app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from backend.app.schemas.score import PredictionScoreRequest, PredictionScoreResponse
from backend.app.schemas.workflow import WorkflowResponse
from backend.app.services.idx_backtest import run_idx_backtest, run_idx_screener, run_setup_backtest
from backend.app.services.prediction_engine import (
    build_idx_recommendation,
    build_idx_workflow,
    build_performance_report,
    build_prediction,
    build_watchlist,
    train_weight_profile,
)
from backend.app.services.score_engine import build_prediction_score

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


@router.get("/prediction/score", response_model=PredictionScoreResponse)
async def read_prediction_score(
    ticker: str = Query(default="BBCA"),
    horizon: str = Query(default="weekly"),
    market: str = Query(default="id"),
    session: AsyncSession = Depends(get_session),
) -> PredictionScoreResponse:
    try:
        report = await build_prediction_score(session, ticker, horizon=horizon, market=market)
        return PredictionScoreResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membuat score prediksi: {exc}")


@router.post("/prediction/score", response_model=PredictionScoreResponse)
async def read_prediction_score_post(
    request: PredictionScoreRequest,
    session: AsyncSession = Depends(get_session),
) -> PredictionScoreResponse:
    try:
        report = await build_prediction_score(
            session,
            request.ticker,
            horizon=request.horizon,
            market=request.market,
            backtest_start=request.backtest_start,
            backtest_end=request.backtest_end,
        )
        return PredictionScoreResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membuat score prediksi: {exc}")


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


@router.get("/workflow/idx", response_model=WorkflowResponse)
async def read_idx_workflow(
    tickers: str = Query(default="BBCA,BBRI,BMRI,TLKM,ASII,BBNI,UNVR,CPIN,ICBP,AMRT"),
    market: str = Query(default="id"),
    session: AsyncSession = Depends(get_session),
) -> WorkflowResponse:
    try:
        report = await build_idx_workflow(session, tickers.split(","), market=market)
        return WorkflowResponse(**report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membaca workflow IDX: {exc}")


@router.get("/recommendations/idx/{ticker}", response_model=RecommendationResponse)
async def read_idx_recommendation(
    ticker: str,
    horizon: str = Query(default="weekly"),
    market: str = Query(default="id"),
    session: AsyncSession = Depends(get_session),
) -> RecommendationResponse:
    try:
        report = await build_idx_recommendation(session, ticker, horizon=horizon, market=market)
        return RecommendationResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membuat rekomendasi IDX: {exc}")


@router.post("/recommendations/idx", response_model=RecommendationResponse)
async def read_live_idx_recommendation(
    request: RecommendationRequest,
    session: AsyncSession = Depends(get_session),
) -> RecommendationResponse:
    try:
        report = await build_idx_recommendation(
            session,
            request.ticker,
            horizon=request.horizon,
            market=request.market,
            market_data_providers=request.market_data_providers,
        )
        return RecommendationResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membuat rekomendasi IDX: {exc}")


@router.post("/idx/backtest", response_model=BacktestResponse)
async def run_idx_backtest_report(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_session),
) -> BacktestResponse:
    try:
        report = await run_idx_backtest(session, request)
        return BacktestResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal menjalankan backtest IDX: {exc}")


@router.post("/run-idx-screener", response_model=ScreenerResponse)
async def run_idx_screener_report(
    request: ScreenerRequest,
    session: AsyncSession = Depends(get_session),
) -> ScreenerResponse:
    try:
        report = await run_idx_screener(session, request)
        return ScreenerResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal menjalankan IDX screener: {exc}")


@router.post("/idx/backtest/setup", response_model=SetupBacktestResponse)
async def run_idx_setup_backtest(
    request: SetupBacktestRequest,
    session: AsyncSession = Depends(get_session),
) -> SetupBacktestResponse:
    """
    Backtest per setup type (breakout, pullback, continuation, reversal).
    Membantu trader memvalidasi setup mana yang paling reliable untuk saham tertentu.
    """
    try:
        report = await run_setup_backtest(session, request)
        return SetupBacktestResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal menjalankan setup backtest: {exc}")
