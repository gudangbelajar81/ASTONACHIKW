from datetime import date, timedelta
from typing import Any

import pandas as pd
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.market import fetch_market_data

POSITIVE_TERMS = {
    "beat",
    "beats",
    "bullish",
    "buy",
    "growth",
    "higher",
    "outperform",
    "profit",
    "raise",
    "raises",
    "record",
    "strong",
    "upgrade",
    "upside",
}


def clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def detect_price_regime(df: pd.DataFrame) -> dict[str, float | str]:
    close = df["close"].astype(float)
    returns = close.pct_change().fillna(0)
    latest_close = float(close.iloc[-1])
    sma_50 = float(close.rolling(50, min_periods=10).mean().iloc[-1])
    sma_200 = float(close.rolling(200, min_periods=30).mean().iloc[-1])
    return_20 = latest_close / float(close.iloc[-21]) - 1 if len(close) > 21 else 0.0
    return_60 = latest_close / float(close.iloc[-61]) - 1 if len(close) > 61 else return_20
    realized_volatility = float(returns.rolling(20, min_periods=10).std().iloc[-1] or 0) * (252 ** 0.5)

    trend_score = clamp(((latest_close / sma_50 - 1) * 6 if sma_50 else 0) + ((latest_close / sma_200 - 1) * 4 if sma_200 else 0))
    momentum_score = clamp((return_20 * 5) + (return_60 * 2.5))
    volatility_score = clamp(realized_volatility / 0.45, 0, 1)

    if volatility_score >= 0.78 and momentum_score < -0.15:
        label = "risk-off"
    elif trend_score > 0.22 and momentum_score > 0.12 and volatility_score < 0.65:
        label = "bullish"
    elif trend_score < -0.22 and momentum_score < -0.12:
        label = "bearish"
    elif volatility_score >= 0.72:
        label = "high-volatility"
    else:
        label = "sideways"

    return {"label": label, "trend_score": trend_score, "volatility_score": volatility_score, "momentum_score": momentum_score}


async def load_market_frame(ticker: str, lookback_days: int = 282) -> pd.DataFrame:
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    df = fetch_market_data(ticker.upper(), start, end)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.sort_values("date").reset_index(drop=True)

NEGATIVE_TERMS = {
    "bearish",
    "cut",
    "cuts",
    "decline",
    "downgrade",
    "drop",
    "falls",
    "fear",
    "loss",
    "miss",
    "misses",
    "probe",
    "risk",
    "sell",
    "slump",
    "weak",
}


def score_headline(text: str) -> float:
    words = {word.strip(".,:;!?()[]{}'\"").lower() for word in text.split()}
    positive = len(words & POSITIVE_TERMS)
    negative = len(words & NEGATIVE_TERMS)
    if positive == 0 and negative == 0:
        return 0.0
    return clamp((positive - negative) / max(positive + negative, 1))


def extract_news_items(raw_news: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    items = []
    for item in raw_news[:limit]:
        title = item.get("title") or item.get("content", {}).get("title") or ""
        publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName") or "Unknown"
        link = item.get("link") or item.get("content", {}).get("canonicalUrl", {}).get("url") or ""
        if not title:
            continue
        items.append(
            {
                "title": title,
                "publisher": publisher,
                "url": link,
                "score": score_headline(title),
            }
        )
    return items


async def build_sentiment_context(ticker: str) -> dict[str, Any]:
    symbol = ticker.upper()
    try:
        news = yf.Ticker(symbol).news or []
    except Exception:
        news = []

    items = extract_news_items(news)
    average_score = sum(item["score"] for item in items) / len(items) if items else 0.0
    if average_score >= 0.18:
        label = "positif"
    elif average_score <= -0.18:
        label = "negatif"
    else:
        label = "netral"

    return {
        "ticker": symbol,
        "label": label,
        "score": average_score,
        "headline_count": len(items),
        "items": items,
        "description": (
            "Sentimen headline mendukung bias positif."
            if label == "positif"
            else "Sentimen headline memberi tekanan negatif."
            if label == "negatif"
            else "Sentimen headline masih campuran atau minim sinyal."
        ),
    }


async def build_macro_context(
    session: AsyncSession,
    ticker: str,
    benchmark: str = "SPY",
    lookback_days: int = 252,
) -> dict[str, Any]:
    symbol = ticker.upper()
    benchmark_symbol = benchmark.upper()
    ticker_df = await load_market_frame(symbol, lookback_days + 30)
    benchmark_df = await load_market_frame(benchmark_symbol, lookback_days + 30)

    left = ticker_df[["date", "close"]].rename(columns={"close": "ticker_close"})
    right = benchmark_df[["date", "close"]].rename(columns={"close": "benchmark_close"})
    merged = pd.merge(left, right, on="date", how="inner").tail(lookback_days)

    if len(merged) < 60:
        return {
            "benchmark": benchmark_symbol,
            "beta": 1.0,
            "correlation": 0.0,
            "relative_strength": 0.0,
            "market_regime": "unknown",
            "risk_budget": "normal",
            "description": "Data benchmark belum cukup untuk konteks makro.",
        }

    ticker_returns = merged["ticker_close"].pct_change().dropna()
    benchmark_returns = merged["benchmark_close"].pct_change().dropna()
    aligned = pd.concat([ticker_returns, benchmark_returns], axis=1).dropna()
    aligned.columns = ["ticker", "benchmark"]

    correlation = float(aligned["ticker"].corr(aligned["benchmark"]))
    benchmark_variance = float(aligned["benchmark"].var())
    beta = float(aligned["ticker"].cov(aligned["benchmark"]) / benchmark_variance) if benchmark_variance else 1.0
    ticker_return_60 = float(merged["ticker_close"].iloc[-1] / merged["ticker_close"].iloc[-61] - 1)
    benchmark_return_60 = float(merged["benchmark_close"].iloc[-1] / merged["benchmark_close"].iloc[-61] - 1)
    relative_strength = ticker_return_60 - benchmark_return_60
    benchmark_regime = detect_price_regime(benchmark_df)

    if benchmark_regime["label"] in {"risk-off", "bearish"} or beta > 1.4:
        risk_budget = "defensif"
    elif benchmark_regime["label"] == "bullish" and relative_strength > 0:
        risk_budget = "agresif-terukur"
    else:
        risk_budget = "normal"

    return {
        "benchmark": benchmark_symbol,
        "beta": beta,
        "correlation": correlation,
        "relative_strength": relative_strength,
        "market_regime": benchmark_regime["label"],
        "risk_budget": risk_budget,
        "description": (
            f"{symbol} memiliki beta {beta:.2f} terhadap {benchmark_symbol}, "
            f"korelasi {correlation:.2f}, dan relative strength {relative_strength:.2%} dalam 60 hari."
        ),
    }
