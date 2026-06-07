from datetime import date, timedelta
import json
import re
import urllib.error
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.bandarmology import MarketDataProviderInput
from backend.app.services.provider_normalizer import normalize_bandarmology_record
from backend.app.services.prediction_engine import clamp, load_price_frame


def enrich_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy().sort_values("date").reset_index(drop=True)
    close = enriched["close"].astype(float)
    enriched["ma20"] = close.rolling(20, min_periods=5).mean()
    enriched["ma50"] = close.rolling(50, min_periods=10).mean()
    enriched["ma200"] = close.rolling(200, min_periods=30).mean()
    return enriched


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    direction = close.diff().fillna(0).apply(lambda value: 1 if value > 0 else -1 if value < 0 else 0)
    return (direction * volume).cumsum()


def calculate_money_flow_score(df: pd.DataFrame) -> float:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    typical = (high + low + close) / 3
    raw_flow = typical * volume
    positive = raw_flow.where(typical.diff().fillna(0) > 0, 0).tail(14).sum()
    negative = raw_flow.where(typical.diff().fillna(0) < 0, 0).tail(14).sum()
    if positive + negative <= 0:
        return 0.0
    money_flow_index = 100 - (100 / (1 + positive / max(abs(negative), 1)))
    return clamp((float(money_flow_index) - 50) / 50)


def calculate_accumulation_distribution(df: pd.DataFrame) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    money_flow_multiplier = ((close - low) - (high - close)) / (high - low).replace(0, 1)
    return (money_flow_multiplier.fillna(0) * volume).cumsum()


def build_bandarmology(df: pd.DataFrame, ticker: str) -> dict:
    if df.empty:
        raise ValueError("Data OHLCV kosong.")

    enriched = enrich_ohlcv(df)
    latest = enriched.iloc[-1]
    volume = enriched["volume"].astype(float)
    close = enriched["close"].astype(float)
    obv = calculate_obv(enriched)
    ad_line = calculate_accumulation_distribution(enriched)

    avg_volume_20 = float(volume.rolling(20, min_periods=5).mean().iloc[-1] or 0)
    volume_spike = float(volume.iloc[-1] / avg_volume_20) if avg_volume_20 > 0 else 0.0
    recent_close_position = float(((latest.close - latest.low) / max(latest.high - latest.low, 0.01)) * 2 - 1)
    obv_slope = float(obv.tail(10).iloc[-1] - obv.tail(10).iloc[0]) if len(obv) >= 10 else 0.0
    ad_slope = float(ad_line.tail(10).iloc[-1] - ad_line.tail(10).iloc[0]) if len(ad_line) >= 10 else 0.0
    volume_pressure = clamp((volume_spike - 1) / 2)
    money_flow_score = calculate_money_flow_score(enriched)
    accumulation_score = clamp(
        (1 if ad_slope > 0 else -1 if ad_slope < 0 else 0) * 0.45
        + (1 if obv_slope > 0 else -1 if obv_slope < 0 else 0) * 0.35
        + recent_close_position * 0.2
    )
    distribution_score = clamp(-accumulation_score)
    smart_money_score = clamp(
        accumulation_score * 0.45
        + money_flow_score * 0.25
        + volume_pressure * 0.2
        + recent_close_position * 0.1
    )
    support = float(enriched["low"].tail(30).min())
    resistance = float(enriched["high"].tail(30).max())
    obv_trend = "naik" if obv_slope > 0 else "turun" if obv_slope < 0 else "netral"

    notes = []
    if volume_spike >= 1.8 and latest.close >= latest.open:
        notes.append("Volume spike muncul saat candle hijau, indikasi akumulasi proxy.")
    if volume_spike >= 1.8 and latest.close < latest.open:
        notes.append("Volume spike muncul saat candle merah, waspadai distribusi.")
    if obv_trend == "naik":
        notes.append("OBV cenderung naik, volume mendukung kenaikan harga.")
    if money_flow_score > 0.25:
        notes.append("Money flow proxy positif.")
    if not notes:
        notes.append("Belum ada sinyal bandar proxy yang dominan.")

    if smart_money_score >= 0.35:
        verdict = "akumulasi"
    elif smart_money_score <= -0.35:
        verdict = "distribusi"
    else:
        verdict = "netral"

    return {
        "ticker": ticker.upper(),
        "as_of_date": str(latest.date),
        "source": "internal",
        "provider_name": None,
        "provider_status": None,
        "smart_money_score": smart_money_score,
        "accumulation_score": accumulation_score,
        "distribution_score": distribution_score,
        "volume_spike": volume_spike,
        "obv_trend": obv_trend,
        "money_flow_score": money_flow_score,
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "verdict": verdict,
        "notes": notes,
    }


def _format_provider_endpoint(endpoint: str, ticker: str, lookback_days: int) -> str:
    ticker_upper = ticker.upper()
    parsed = urlparse(endpoint.strip())
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    replaced_query = []
    saw_ticker_token = False
    saw_days_token = False
    for key, value in query_items:
        normalized_key = key.lower()
        if normalized_key in {"ticker", "symbol", "code", "stock", "saham"}:
            replaced_query.append((key, ticker_upper))
            saw_ticker_token = True
        elif normalized_key in {"days", "lookback_days", "window"}:
            replaced_query.append((key, str(lookback_days)))
            saw_days_token = True
        else:
            replaced_query.append((key, value))

    path = parsed.path
    if "{ticker}" in path:
        path = path.replace("{ticker}", ticker_upper)
        saw_ticker_token = True
    if "{{ticker}}" in path:
        path = path.replace("{{ticker}}", ticker_upper)
        saw_ticker_token = True
    if "{days}" in path:
        path = path.replace("{days}", str(lookback_days))
        saw_days_token = True
    if "{lookback_days}" in path:
        path = path.replace("{lookback_days}", str(lookback_days))
        saw_days_token = True

    segments = [segment for segment in path.split("/") if segment]
    if not saw_ticker_token and segments:
        for index in range(len(segments) - 1, -1, -1):
            if re.fullmatch(r"[A-Za-z0-9.^_-]{2,15}", segments[index] or ""):
                segments[index] = ticker_upper
                saw_ticker_token = True
                break
        path = "/" + "/".join(segments) if segments else path

    if not saw_days_token:
        replaced_query.append(("days", str(lookback_days)))

    return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, urlencode(replaced_query), parsed.fragment))


def _request_provider_json(provider: MarketDataProviderInput, ticker: str, lookback_days: int) -> dict:
    url = _format_provider_endpoint(provider.endpoint, ticker, lookback_days)
    parsed = urlparse(url)
    headers = {"Accept": "application/json"}
    if "rapidapi.com" in parsed.netloc or ".rapidapi.com" in parsed.netloc:
        headers["X-RapidAPI-Key"] = provider.api_key
        headers["X-RapidAPI-Host"] = parsed.netloc
    else:
        headers["Authorization"] = f"Bearer {provider.api_key}"
        headers["X-Api-Key"] = provider.api_key

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(body)
            detail = payload.get("msg") or payload.get("message") or payload.get("detail") or body
        except json.JSONDecodeError:
            detail = body or str(exc)
        raise ValueError(detail) from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Gagal menghubungi provider: {exc.reason}") from exc


def _stringify_notes(payload: object) -> list[str]:
    notes: list[str] = []
    if payload is None:
        return notes
    if isinstance(payload, str):
        text = payload.strip()
        if text:
            notes.append(text)
        return notes
    if isinstance(payload, list):
        for item in payload:
            notes.extend(_stringify_notes(item))
        return notes
    if isinstance(payload, dict):
        for key in ("notes", "note", "message", "messages", "detail", "summary", "analysis", "commentary"):
            value = payload.get(key)
            if value:
                notes.extend(_stringify_notes(value))
        return notes
    return notes


def _extract_first_number(payload: dict, keys: list[str]) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace("%", "").replace("x", "").strip())
            except ValueError:
                continue
    return None


def _extract_first_string(payload: dict, keys: list[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalize_provider_bandarmology(payload: object, ticker: str, provider_name: str) -> dict:
    source = "live"
    provider_status = "live"
    normalized_broker = normalize_bandarmology_record(payload, ticker, provider_name)
    candidate = payload
    if isinstance(payload, dict):
        for key in ("data", "result", "payload", "output", "bandarmology", "analysis"):
            value = payload.get(key)
            if value:
                candidate = value
                break

    if isinstance(candidate, dict):
        broker_score = normalized_broker["broker_accumulation_score"]
        normalized_smart_money = clamp((broker_score - 50) / 50) if broker_score else 0.0
        smart_money_score = _extract_first_number(candidate, ["smart_money_score", "smartMoneyScore", "smartMoney", "score"]) or normalized_smart_money
        accumulation_score = _extract_first_number(candidate, ["accumulation_score", "accumulationScore", "buy_score"]) or smart_money_score
        distribution_score = _extract_first_number(candidate, ["distribution_score", "distributionScore", "sell_score"]) or (-accumulation_score)
        volume_spike = _extract_first_number(candidate, ["volume_spike", "volumeSpike", "volume_ratio", "volumeRatio"]) or 0.0
        money_flow_score = _extract_first_number(candidate, ["money_flow_score", "moneyFlowScore", "mfi_score", "mfiScore"]) or 0.0
        support = _extract_first_number(candidate, ["support", "support_level", "supportLevel"]) or 0.0
        resistance = _extract_first_number(candidate, ["resistance", "resistance_level", "resistanceLevel"]) or 0.0
        obv_trend = _extract_first_string(candidate, ["obv_trend", "obvTrend", "obv", "trend"]) or "netral"
        verdict = _extract_first_string(candidate, ["verdict", "signal", "status"]) or ""
        notes = _stringify_notes(candidate)

        if not notes:
            for key in ("net_buy", "net_sell", "foreign_net_buy", "foreign_net_sell", "broker", "broker_summary"):
                if key in candidate:
                    notes.extend(_stringify_notes(candidate[key]))
        if normalized_broker["net_buy_value"]:
            notes.append(f"Net buy value provider: {normalized_broker['net_buy_value']:.0f}.")
        if normalized_broker["top_buyer_brokers"]:
            notes.append(f"Top buyer broker: {', '.join(normalized_broker['top_buyer_brokers'][:5])}.")
        if normalized_broker["top_seller_brokers"]:
            notes.append(f"Top seller broker: {', '.join(normalized_broker['top_seller_brokers'][:5])}.")

        if not verdict:
            if smart_money_score >= 0.35:
                verdict = "akumulasi"
            elif smart_money_score <= -0.35:
                verdict = "distribusi"
            else:
                verdict = "netral"

        if not notes:
            notes = ["Provider live aktif, tetapi detail sinyal belum sepenuhnya terstruktur. Gunakan nilai utama dan ringkasan provider sebagai acuan."]

        return {
            "ticker": ticker.upper(),
            "as_of_date": str(candidate.get("as_of_date") or candidate.get("date") or date.today()),
            "source": source,
            "provider_name": provider_name,
            "provider_status": provider_status,
            "smart_money_score": float(smart_money_score),
            "accumulation_score": float(accumulation_score),
            "distribution_score": float(distribution_score),
            "volume_spike": float(volume_spike),
            "obv_trend": obv_trend,
            "money_flow_score": float(money_flow_score),
            "support": float(support),
            "resistance": float(resistance),
            "verdict": verdict,
            "notes": notes,
            "normalized_provider_data": normalized_broker,
            "raw": candidate,
        }

    return {
        "ticker": ticker.upper(),
        "as_of_date": str(date.today()),
        "source": source,
        "provider_name": provider_name,
        "provider_status": provider_status,
        "smart_money_score": 0.0,
        "accumulation_score": 0.0,
        "distribution_score": 0.0,
        "volume_spike": 0.0,
        "obv_trend": "netral",
        "money_flow_score": 0.0,
        "support": 0.0,
        "resistance": 0.0,
        "verdict": "netral",
        "notes": ["Provider live merespons format yang belum terstruktur. Simpan raw response untuk penyesuaian mapper."],
        "normalized_provider_data": normalized_broker,
        "raw": candidate,
    }


def build_live_bandarmology(df: pd.DataFrame, ticker: str, provider: MarketDataProviderInput | None, lookback_days: int) -> dict:
    internal = build_bandarmology(df, ticker)
    if not provider:
        return internal

    try:
        payload = _request_provider_json(provider, ticker, lookback_days)
        normalized = normalize_provider_bandarmology(payload, ticker, provider.id)
        merged = {**internal, **normalized}
        merged["points"] = internal.get("points", [])
        return merged
    except Exception as exc:
        fallback = {**internal}
        fallback["source"] = "internal_fallback"
        fallback["provider_name"] = provider.id
        fallback["provider_status"] = "dead"
        fallback["notes"] = internal.get("notes", []) + [f"Provider live gagal: {exc}"]
        return fallback


async def build_ohlcv_report(session: AsyncSession, ticker: str, lookback_days: int = 260) -> dict:
    df = await load_price_frame(session, ticker.upper(), max(lookback_days, 260))
    enriched = enrich_ohlcv(df).tail(lookback_days)
    points = []
    for row in enriched.itertuples(index=False):
        points.append(
            {
                "date": row.date.isoformat() if hasattr(row.date, "isoformat") else str(row.date),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume or 0),
                "ma20": None if pd.isna(row.ma20) else float(row.ma20),
                "ma50": None if pd.isna(row.ma50) else float(row.ma50),
                "ma200": None if pd.isna(row.ma200) else float(row.ma200),
            }
        )

    return {
        "ticker": ticker.upper(),
        "points": points,
        "bandarmology": build_bandarmology(enriched, ticker),
    }


async def build_ohlcv_live_report(
    session: AsyncSession,
    ticker: str,
    lookback_days: int,
    market_data_providers: list[MarketDataProviderInput] | None = None,
) -> dict:
    df = await load_price_frame(session, ticker.upper(), max(lookback_days, 260))
    enriched = enrich_ohlcv(df).tail(lookback_days)
    points = []
    for row in enriched.itertuples(index=False):
        points.append(
            {
                "date": row.date.isoformat() if hasattr(row.date, "isoformat") else str(row.date),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume or 0),
                "ma20": None if pd.isna(row.ma20) else float(row.ma20),
                "ma50": None if pd.isna(row.ma50) else float(row.ma50),
                "ma200": None if pd.isna(row.ma200) else float(row.ma200),
            }
        )

    selected_provider = None
    live_bandarmology = None
    for provider in market_data_providers or []:
        if provider.endpoint and provider.api_key:
            selected_provider = provider
            live_bandarmology = build_live_bandarmology(enriched, ticker, provider, lookback_days)
            break

    return {
        "ticker": ticker.upper(),
        "points": points,
        "bandarmology": live_bandarmology or build_bandarmology(enriched, ticker),
        "market_data_provider": selected_provider.id if selected_provider else None,
    }
