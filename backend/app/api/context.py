from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.schemas.context import MacroContextResponse, SentimentResponse
from backend.app.services.context_engine import build_macro_context, build_sentiment_context

router = APIRouter(tags=["context"])


@router.get("/sentiment/{ticker}", response_model=SentimentResponse)
async def read_sentiment(ticker: str) -> SentimentResponse:
    try:
        return SentimentResponse(**await build_sentiment_context(ticker))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membaca sentimen: {exc}")


@router.get("/macro/{ticker}", response_model=MacroContextResponse)
async def read_macro_context(
    ticker: str,
    benchmark: str = Query(default="SPY"),
    session: AsyncSession = Depends(get_session),
) -> MacroContextResponse:
    try:
        return MacroContextResponse(**await build_macro_context(session, ticker, benchmark))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal membaca konteks makro: {exc}")
