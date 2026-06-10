from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.session import get_session
from backend.app.services.dsi_radar_engine import build_dsi_radar
from backend.app.services.idx_backtest import IDX_UNIVERSE
from backend.app.services.prediction_engine import normalize_backend_ticker

router = APIRouter(tags=["dsi_radar"])


class DSIRadarRequest(BaseModel):
    tickers: list[str] = Field(
        default_factory=list,
        description="List kode saham. Kosong = pakai IDX Universe default.",
        max_length=50,
    )
    market: str = Field(default="id", description="'id' untuk IDX, 'us' untuk US market.")
    eodhd_api_key: str = Field(default="", description="Override EODHD API key (opsional).")


class EODHDKeyRequest(BaseModel):
    api_key: str = Field(..., description="EODHD API key dari eodhd.com")


@router.post("/dsi-radar")
async def get_dsi_radar(
    body: DSIRadarRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    DSI Command Center — Multi-Ticker × Multi-Timeframe Radar.

    Jika EODHD_API_KEY dikonfigurasi di settings atau dikirim di body,
    akan menggunakan data intraday sungguhan dari EODHD.com.
    Jika tidak, fallback ke proxy data harian (Yahoo Finance).

    Signal:
    - 🟢 HAKA  : DSI(15m) > 60 dan harga di atas VWAP
    - 🔵 IMBAL : harga > 3% di bawah VWAP → potensi rebound
    - ⚪ PANTU : kondisi lainnya → netral

    Returns:
        rows: list DSIRadarRow per ticker, diurutkan HAKA → IMBAL → PANTU
    """
    tickers = body.tickers or IDX_UNIVERSE[:30]

    seen: set[str] = set()
    clean: list[str] = []
    for t in tickers:
        norm = normalize_backend_ticker(t.strip(), body.market)
        if norm and norm not in seen:
            seen.add(norm)
            clean.append(t.strip())
        if len(clean) >= 50:
            break

    # Ambil API key: dari request body (override) atau settings
    api_key = body.eodhd_api_key.strip() or getattr(settings, "EODHD_API_KEY", "")

    try:
        result = await build_dsi_radar(
            session, clean,
            market=body.market,
            eodhd_api_key=api_key or None,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DSI Radar gagal: {exc}")


@router.post("/eodhd/test-key")
async def test_eodhd_key(body: EODHDKeyRequest) -> dict:
    """
    Test koneksi ke EODHD API dengan API key yang diberikan.
    Returns: {"status": "live"|"dead", "detail": str}
    """
    if not body.api_key.strip():
        return {"status": "dead", "detail": "API key kosong."}
    try:
        from backend.app.services.eodhd_provider import test_eodhd_connection
        result = test_eodhd_connection(body.api_key.strip())
        return result
    except Exception as exc:
        return {"status": "dead", "detail": str(exc)}


@router.get("/eodhd/status")
async def eodhd_status() -> dict:
    """Cek apakah EODHD API key sudah dikonfigurasi di backend."""
    key = getattr(settings, "EODHD_API_KEY", "")
    enabled = getattr(settings, "EODHD_ENABLED", True)
    return {
        "configured": bool(key),
        "enabled": enabled,
        "exchange": getattr(settings, "EODHD_EXCHANGE", "JK"),
        "masked_key": f"{key[:6]}...{key[-4:]}" if len(key) > 10 else ("*" * len(key) if key else ""),
    }

