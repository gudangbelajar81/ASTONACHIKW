"""
News Sentiment Engine — AstroCycle v2
======================================
Mengambil berita saham IDX dari sumber publik (RSS) dan menghitung
skor sentimen berbasis keyword tanpa memerlukan API berbayar.

Sumber data (gratis):
1. Google Finance RSS per ticker
2. IDX.co.id news RSS
3. Fallback: skor netral

Bobot sentimen dalam final_weighted_score:
  final_weighted_score = (technical_score * 0.75) + (news_score_normalized * 25)
"""

from __future__ import annotations

import asyncio
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ── Kata kunci penentu sentimen ──────────────────────────────────────────────

POSITIVE_KEYWORDS = [
    # Kinerja keuangan
    "laba naik", "laba meningkat", "profit naik", "profit meningkat",
    "pendapatan naik", "pendapatan meningkat", "rekor laba", "rekor pendapatan",
    "kinerja positif", "kinerja baik", "kinerja meningkat",
    # Aksi korporasi positif
    "dividen", "buyback", "akuisisi strategis", "ekspansi", "go public",
    "ipo sukses", "rights issue positif", "stock split",
    "kontrak baru", "memenangkan tender", "proyek baru",
    # Sentimen pasar positif
    "upgrade", "outperform", "overweight", "target naik", "rekomendasi beli",
    "masuk indeks", "ihsg positif",
    # Operasional
    "produksi naik", "kapasitas naik", "penjualan naik", "volume naik",
    "pangsa pasar naik", "ekspor naik",
]

NEGATIVE_KEYWORDS = [
    # Kinerja keuangan negatif
    "rugi", "merugi", "laba turun", "laba anjlok", "laba menurun",
    "pendapatan turun", "pendapatan anjlok", "kinerja turun", "kinerja memburuk",
    # Masalah hukum & regulator
    "kena sanksi", "denda", "investigasi", "kasus hukum", "gugatan",
    "suspensi saham", "delisting", "pailit", "gagal bayar", "default",
    "kredit macet",
    # Aksi korporasi negatif
    "divestasi paksa", "rights issue terpaksa", "utang naik", "beban naik",
    # Sentimen pasar negatif
    "downgrade", "underperform", "underweight", "target turun",
    "rekomendasi jual", "keluar indeks",
    # Operasional
    "produksi turun", "penjualan turun", "ekspor turun", "pemogokan",
    "kebakaran pabrik", "bencana",
]

NEUTRAL_BOOST_KEYWORDS = [
    "rapat umum", "rups", "laporan keuangan", "kuartal", "semester",
    "tbk", "pengumuman", "keterbukaan informasi",
]


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class NewsSentiment:
    ticker: str
    score: float = 0.5                    # 0.0 sangat negatif → 1.0 sangat positif
    label: str = "neutral"               # "positive" | "neutral" | "negative"
    headlines: list[str] = field(default_factory=list)
    source: str = "fallback_neutral"
    fetched_at: str = ""
    headline_count: int = 0

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "news_sentiment_score": round(self.score, 3),
            "news_sentiment_label": self.label,
            "news_headlines": self.headlines[:5],
            "news_source": self.source,
            "news_fetched_at": self.fetched_at,
            "news_headline_count": self.headline_count,
        }


# ── Helper: Bersihkan teks HTML ───────────────────────────────────────────────

def _clean_text(raw: str) -> str:
    """Hapus tag HTML dan decode HTML entities."""
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = html.unescape(clean)
    return " ".join(clean.split()).lower()


# ── Scoring berbasis keyword ──────────────────────────────────────────────────

def _score_text(text: str) -> float:
    """
    Hitung skor sentimen dari teks berita.
    Returns float 0.0–1.0, dengan 0.5 = netral.
    """
    pos_hits = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    neg_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

    total = pos_hits + neg_hits
    if total == 0:
        return 0.5  # netral

    # Bobot lebih berat ke negatif (risk-management mindset)
    raw = (pos_hits - neg_hits * 1.3) / max(total, 1)
    # Normalisasi ke 0–1 dengan sigmoid-like clamp
    normalized = 0.5 + (raw * 0.4)
    return round(max(0.0, min(1.0, normalized)), 4)


def _label_from_score(score: float) -> str:
    if score >= 0.60:
        return "positive"
    if score <= 0.40:
        return "negative"
    return "neutral"


# ── Fetch RSS (sync, di-run di thread pool) ───────────────────────────────────

def _fetch_google_finance_rss(ticker: str, timeout: int = 8) -> list[str]:
    """
    Ambil berita dari Google Finance RSS.
    Format: ticker IDX biasanya {TICKER}:IDX (misal BBCA:IDX)
    """
    idx_ticker = ticker.replace(".JK", "").upper()
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={idx_ticker}.JK&region=ID&lang=id-ID"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AstroCycle/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="replace")
        root = ET.fromstring(content)
        titles = []
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                titles.append(title_el.text.strip())
        return titles[:10]
    except Exception:
        return []


def _fetch_idx_rss(timeout: int = 10) -> list[str]:
    """
    Ambil berita umum IDX dari RSS resmi.
    """
    url = "https://www.idx.co.id/umum/berita-dan-pengumuman/rss/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AstroCycle/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="replace")
        root = ET.fromstring(content)
        titles = []
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                titles.append(title_el.text.strip())
        return titles[:30]
    except Exception:
        return []


# ── Core: Analisis sentimen satu ticker ──────────────────────────────────────

def _analyze_ticker_sentiment(ticker: str, idx_news: list[str]) -> NewsSentiment:
    """
    Analisis sentimen untuk satu ticker.
    Menggabungkan berita spesifik (Yahoo Finance RSS) + berita IDX umum.
    """
    clean_ticker = ticker.replace(".JK", "").replace(".IDX", "").upper()
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Ambil berita spesifik ticker dari Yahoo Finance RSS
    specific_headlines = _fetch_google_finance_rss(ticker)

    # 2. Filter berita IDX umum yang menyebut ticker ini
    relevant_idx = [
        h for h in idx_news
        if clean_ticker in h.upper()
    ]

    all_headlines = specific_headlines + relevant_idx
    all_text = " ".join(_clean_text(h) for h in all_headlines)

    if not all_headlines:
        return NewsSentiment(
            ticker=ticker,
            score=0.5,
            label="neutral",
            headlines=[],
            source="fallback_neutral",
            fetched_at=fetched_at,
            headline_count=0,
        )

    score = _score_text(all_text)
    label = _label_from_score(score)
    source = "yahoo_finance_rss" if specific_headlines else "idx_rss_filtered"

    return NewsSentiment(
        ticker=ticker,
        score=score,
        label=label,
        headlines=(specific_headlines + relevant_idx)[:5],
        source=source,
        fetched_at=fetched_at,
        headline_count=len(all_headlines),
    )


# ── Fungsi publik: Ambil sentimen batch ──────────────────────────────────────

async def fetch_news_sentiment(tickers: list[str]) -> dict[str, NewsSentiment]:
    """
    Ambil dan hitung sentimen berita untuk sekumpulan ticker secara async.

    Args:
        tickers: List kode saham IDX (misal ["BBCA", "TLKM", "GOTO"])

    Returns:
        Dict {ticker: NewsSentiment}
    """
    loop = asyncio.get_event_loop()

    # Ambil berita umum IDX sekali saja (efisien)
    idx_news: list[str] = []
    try:
        idx_news = await loop.run_in_executor(None, _fetch_idx_rss)
    except Exception:
        idx_news = []

    # Analisis per ticker secara paralel di thread pool
    tasks = [
        loop.run_in_executor(None, _analyze_ticker_sentiment, ticker, idx_news)
        for ticker in tickers
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    sentiment_map: dict[str, NewsSentiment] = {}
    for ticker, result in zip(tickers, results):
        if isinstance(result, NewsSentiment):
            sentiment_map[ticker] = result
        else:
            # Fallback jika terjadi error
            sentiment_map[ticker] = NewsSentiment(
                ticker=ticker,
                score=0.5,
                label="neutral",
                headlines=[],
                source="error_fallback",
                fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                headline_count=0,
            )

    return sentiment_map


# ── Fungsi penimbangan ulang ranking ─────────────────────────────────────────

def apply_news_sentiment_weighting(
    items: list[dict],
    sentiment_map: dict[str, "NewsSentiment"],
    technical_weight: float = 0.75,
    sentiment_weight: float = 0.25,
) -> list[dict]:
    """
    Gabungkan skor teknikal dan sentimen berita untuk ranking final.

    Formula:
        final_weighted_score = (final_score * tech_w) + (news_score_normalized * sent_w)
        
    dimana news_score_normalized = news_sentiment_score * 100
    """
    for item in items:
        ticker = item.get("symbol", "")
        clean_ticker = ticker.replace(".JK", "").replace(".IDX", "").upper()
        
        sentiment = sentiment_map.get(ticker) or sentiment_map.get(clean_ticker)
        if sentiment:
            news_score_normalized = sentiment.score * 100  # 0–100
            item["news_sentiment_score"] = round(sentiment.score, 3)
            item["news_sentiment_label"] = sentiment.label
            item["news_headlines"] = sentiment.headlines
            item["news_source"] = sentiment.source
            item["news_headline_count"] = sentiment.headline_count
        else:
            news_score_normalized = 50.0  # netral default
            item["news_sentiment_score"] = 0.5
            item["news_sentiment_label"] = "neutral"
            item["news_headlines"] = []
            item["news_source"] = "no_data"
            item["news_headline_count"] = 0

        technical_score = item.get("final_score", 0)
        item["final_weighted_score"] = round(
            (technical_score * technical_weight) + (news_score_normalized * sentiment_weight),
            2,
        )

    # Urutkan berdasarkan skor gabungan tertinggi
    items.sort(key=lambda x: x.get("final_weighted_score", 0), reverse=True)
    return items
