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

export type MarketMode = "us" | "id";

export type PlanTier = "free" | "pro";

export type PlanProfile = {
  tier: PlanTier;
  dailyApiLimit: number;
  monthlyReportLimit: number;
};

export type UsageEvent = {
  id: string;
  action: string;
  ticker: string;
  source: string;
  createdAt: string;
};

const ALERTS_KEY = "astrocycle_user_alerts";
const PORTFOLIO_KEY = "astrocycle_portfolio_holdings";
const WATCHLISTS_KEY = "astrocycle_saved_watchlists";
const REPORT_HISTORY_KEY = "astrocycle_report_history";
const MARKET_MODE_KEY = "astrocycle_market_mode";
const USAGE_LOG_KEY = "astrocycle_usage_log";
const PLAN_PROFILE_KEY = "astrocycle_plan_profile";

const DEFAULT_PLAN_PROFILE: PlanProfile = {
  tier: "free",
  dailyApiLimit: 50,
  monthlyReportLimit: 100,
};

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

export function readMarketMode(): MarketMode {
  return readJson<MarketMode>(MARKET_MODE_KEY, "us");
}

export function writeMarketMode(mode: MarketMode) {
  writeJson(MARKET_MODE_KEY, mode);
}

export function normalizeTickerForMarket(value: string, mode: MarketMode = readMarketMode()) {
  const normalized = value.trim().toUpperCase();
  if (!normalized) return "";
  if (mode === "id" && !normalized.includes(".")) {
    return `${normalized}.JK`;
  }
  return normalized;
}

export function normalizeTickerList(raw: string, mode: MarketMode = readMarketMode()) {
  return raw
    .split(",")
    .map((value) => normalizeTickerForMarket(value, mode))
    .filter(Boolean);
}

export function readPlanProfile(): PlanProfile {
  return readJson<PlanProfile>(PLAN_PROFILE_KEY, DEFAULT_PLAN_PROFILE);
}

export function writePlanProfile(profile: PlanProfile) {
  writeJson(PLAN_PROFILE_KEY, profile);
}

export function readUsageLog(): UsageEvent[] {
  return readJson<UsageEvent[]>(USAGE_LOG_KEY, []);
}

export function appendUsageEvent(event: Omit<UsageEvent, "id" | "createdAt">) {
  const history = readUsageLog();
  const next = [
    {
      id: makeId(),
      createdAt: new Date().toISOString(),
      ...event,
    },
    ...history,
  ].slice(0, 200);
  writeJson(USAGE_LOG_KEY, next);
  return next;
}

export function exportUserData() {
  return {
    alerts: readAlerts(),
    portfolio: readPortfolio(),
    watchlists: readSavedWatchlists(),
    reports: readReportHistory(),
    usage: readUsageLog(),
    marketMode: readMarketMode(),
    planProfile: readPlanProfile(),
  };
}

export function importUserData(payload: Partial<ReturnType<typeof exportUserData>>) {
  if (payload.alerts) writeAlerts(payload.alerts);
  if (payload.portfolio) writePortfolio(payload.portfolio);
  if (payload.watchlists) writeSavedWatchlists(payload.watchlists);
  if (payload.reports) writeReportHistory(payload.reports);
  if (payload.usage) writeJson(USAGE_LOG_KEY, payload.usage);
  if (payload.marketMode) writeMarketMode(payload.marketMode);
  if (payload.planProfile) writePlanProfile(payload.planProfile);
}
