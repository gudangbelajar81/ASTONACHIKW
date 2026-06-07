export type AlertCondition = "probability_up" | "expected_return" | "risk_label" | "regime";

export type UserAlert = {
  id: string;
  ticker: string;
  condition: AlertCondition;
  operator: ">=" | "<=" | "equals";
  target: string;
  enabled: boolean;
};

export type PortfolioHolding = {
  id: string;
  ticker: string;
  shares: number;
  averagePrice: number;
};

export type SavedWatchlist = {
  id: string;
  name: string;
  tickers: string[];
  createdAt: string;
};

export type ReportLog = {
  id: string;
  ticker: string;
  generatedAt: string;
  signal: string;
  regime: string;
  confidence: string;
};

const ALERTS_KEY = "astrocycle_user_alerts";
const PORTFOLIO_KEY = "astrocycle_portfolio_holdings";
const WATCHLISTS_KEY = "astrocycle_saved_watchlists";
const REPORT_HISTORY_KEY = "astrocycle_report_history";

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    return JSON.parse(localStorage.getItem(key) ?? "") as T;
  } catch {
    return fallback;
  }
}

function writeJson<T>(key: string, value: T) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function readAlerts(): UserAlert[] {
  return readJson<UserAlert[]>(ALERTS_KEY, []);
}

export function writeAlerts(alerts: UserAlert[]) {
  writeJson(ALERTS_KEY, alerts);
}

export function readPortfolio(): PortfolioHolding[] {
  return readJson<PortfolioHolding[]>(PORTFOLIO_KEY, []);
}

export function writePortfolio(holdings: PortfolioHolding[]) {
  writeJson(PORTFOLIO_KEY, holdings);
}

export function readSavedWatchlists(): SavedWatchlist[] {
  return readJson<SavedWatchlist[]>(WATCHLISTS_KEY, []);
}

export function writeSavedWatchlists(watchlists: SavedWatchlist[]) {
  writeJson(WATCHLISTS_KEY, watchlists);
}

export function readReportHistory(): ReportLog[] {
  return readJson<ReportLog[]>(REPORT_HISTORY_KEY, []);
}

export function writeReportHistory(history: ReportLog[]) {
  writeJson(REPORT_HISTORY_KEY, history);
}

export function appendReportLog(log: Omit<ReportLog, "id" | "generatedAt">) {
  const history = readReportHistory();
  const next = [
    {
      id: makeId(),
      generatedAt: new Date().toISOString(),
      ...log,
    },
    ...history,
  ].slice(0, 50);
  writeReportHistory(next);
  return next;
}

export function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
