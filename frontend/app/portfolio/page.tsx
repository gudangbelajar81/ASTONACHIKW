"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar";
import { PortfolioHolding, makeId, readPortfolio, writePortfolio } from "../../lib/userData";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type EnrichedHolding = PortfolioHolding & {
  lastPrice: number;
  marketValue: number;
  costBasis: number;
  pnl: number;
  pnlPct: number;
  smartMoneyScore?: number;
  verdict?: string;
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [enriched, setEnriched] = useState<EnrichedHolding[]>([]);
  const [ticker, setTicker] = useState("AAPL");
  const [shares, setShares] = useState("10");
  const [averagePrice, setAveragePrice] = useState("150");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function save(nextHoldings: PortfolioHolding[]) {
    setHoldings(nextHoldings);
    writePortfolio(nextHoldings);
  }

  const refreshPortfolio = useCallback(async (nextHoldings: PortfolioHolding[]) => {
    setLoading(true);
    setError("");
    try {
      const rows: EnrichedHolding[] = [];
      for (const holding of nextHoldings) {
        const response = await fetch(`${API_BASE_URL}/api/ohlcv/${encodeURIComponent(holding.ticker)}?lookback_days=90`);
        if (!response.ok) continue;
        const report = await response.json();
        const lastPrice = Number(report.points?.at(-1)?.close ?? holding.averagePrice);
        const marketValue = lastPrice * holding.shares;
        const costBasis = holding.averagePrice * holding.shares;
        rows.push({
          ...holding,
          lastPrice,
          marketValue,
          costBasis,
          pnl: marketValue - costBasis,
          pnlPct: costBasis > 0 ? (marketValue - costBasis) / costBasis : 0,
          smartMoneyScore: report.bandarmology?.smart_money_score,
          verdict: report.bandarmology?.verdict,
        });
      }
      setEnriched(rows);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Gagal memuat portfolio.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const savedHoldings = readPortfolio();
    setHoldings(savedHoldings);
    if (savedHoldings.length) void refreshPortfolio(savedHoldings);
  }, [refreshPortfolio]);

  function addHolding(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextHoldings = [
      ...holdings,
      {
        id: makeId(),
        ticker: ticker.trim().toUpperCase(),
        shares: Number(shares),
        averagePrice: Number(averagePrice),
      },
    ];
    save(nextHoldings);
    void refreshPortfolio(nextHoldings);
  }

  const totals = useMemo(() => {
    const marketValue = enriched.reduce((sum, item) => sum + item.marketValue, 0);
    const costBasis = enriched.reduce((sum, item) => sum + item.costBasis, 0);
    return {
      marketValue,
      costBasis,
      pnl: marketValue - costBasis,
      pnlPct: costBasis > 0 ? (marketValue - costBasis) / costBasis : 0,
    };
  }, [enriched]);

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">Portfolio</p>
            <h1>Portfolio Tracker</h1>
          </div>
          <button className="action-button" type="button" onClick={() => refreshPortfolio(holdings)} disabled={loading || !holdings.length}>
            {loading ? "Memuat..." : "Refresh"}
          </button>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <form className="alert-form" onSubmit={addHolding}>
          <input value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="Ticker" />
          <input value={shares} onChange={(event) => setShares(event.target.value)} type="number" min="0" step="1" />
          <input value={averagePrice} onChange={(event) => setAveragePrice(event.target.value)} type="number" min="0" step="0.01" />
          <button type="submit">Tambah Holding</button>
        </form>

        <section className="prediction-metrics">
          <div><span>Market Value</span><strong>{formatCurrency(totals.marketValue)}</strong></div>
          <div><span>Cost Basis</span><strong>{formatCurrency(totals.costBasis)}</strong></div>
          <div><span>P/L</span><strong>{formatCurrency(totals.pnl)}</strong></div>
          <div><span>P/L %</span><strong>{formatPercent(totals.pnlPct)}</strong></div>
        </section>

        <section className="watchlist-table">
          <div className="portfolio-row portfolio-row--head">
            <span>Ticker</span><span>Shares</span><span>Avg</span><span>Last</span><span>Value</span><span>P/L</span><span>Bandar</span><span></span>
          </div>
          {enriched.length ? enriched.map((holding) => (
            <div className="portfolio-row" key={holding.id}>
              <strong>{holding.ticker}</strong>
              <span>{holding.shares}</span>
              <span>{formatCurrency(holding.averagePrice)}</span>
              <span>{formatCurrency(holding.lastPrice)}</span>
              <span>{formatCurrency(holding.marketValue)}</span>
              <span>{formatCurrency(holding.pnl)} ({formatPercent(holding.pnlPct)})</span>
              <span>{holding.verdict ?? "netral"}</span>
              <button type="button" onClick={() => save(holdings.filter((item) => item.id !== holding.id))}>Hapus</button>
            </div>
          )) : (
            <div className="api-empty">Belum ada holding.</div>
          )}
        </section>
      </main>
    </div>
  );
}
