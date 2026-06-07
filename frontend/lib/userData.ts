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

const ALERTS_KEY = "astrocycle_user_alerts";
const PORTFOLIO_KEY = "astrocycle_portfolio_holdings";

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

export function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
