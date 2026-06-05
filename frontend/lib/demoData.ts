import { AnalystSummary } from "../components/AIInfoPanel";

export type CompositePoint = {
  date: string;
  value: number;
  smoothed_7d: number | null;
  smoothed_30d: number | null;
  smoothed_60d: number | null;
  projected: boolean;
};

export type ScannerResult = {
  cycle: string;
  correlation: number;
  lag_days: number;
  accuracy: number;
  score: number;
  sample_count?: number;
};

export type TurningPoint = {
  date: string;
  type: "TOP" | "BOTTOM" | string;
  strength: number;
};

function formatDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function rollingAverage(values: number[], index: number, window: number) {
  const start = Math.max(0, index - window + 1);
  const slice = values.slice(start, index + 1);
  return slice.reduce((sum, value) => sum + value, 0) / slice.length;
}

function tickerSeed(ticker: string) {
  return ticker.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0) % 17;
}

export function buildDemoComposite(ticker: string): CompositePoint[] {
  const seed = tickerSeed(ticker);
  const today = new Date();
  const totalDays = 210;
  const rawValues = Array.from({ length: totalDays }, (_, index) => {
    const primary = Math.sin((index + seed) / 10);
    const secondary = Math.cos((index + seed * 2) / 23) * 0.35;
    const pulse = Math.sin((index + seed) / 4.5) * 0.14;
    return Math.max(-1, Math.min(1, primary * 0.62 + secondary + pulse));
  });

  return rawValues.map((value, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - 180 + index);

    return {
      date: formatDate(date),
      value,
      smoothed_7d: rollingAverage(rawValues, index, 7),
      smoothed_30d: rollingAverage(rawValues, index, 30),
      smoothed_60d: rollingAverage(rawValues, index, 60),
      projected: index >= 180,
    };
  });
}

export function buildDemoScanner(ticker: string): ScannerResult[] {
  const seed = tickerSeed(ticker) / 100;
  return [
    { cycle: "Venus-Jupiter", correlation: 0.61 + seed, lag_days: 5, accuracy: 0.68, score: 0.64, sample_count: 540 },
    { cycle: "Moon-Venus", correlation: 0.53 + seed, lag_days: 3, accuracy: 0.63, score: 0.59, sample_count: 540 },
    { cycle: "Sun-Mars", correlation: -0.47 - seed, lag_days: 8, accuracy: 0.61, score: 0.53, sample_count: 540 },
    { cycle: "Mercury-Saturn", correlation: 0.41 + seed, lag_days: 13, accuracy: 0.58, score: 0.48, sample_count: 540 },
    { cycle: "Mars-Jupiter", correlation: -0.38 - seed, lag_days: 2, accuracy: 0.56, score: 0.45, sample_count: 540 },
  ];
}

export function buildDemoTurningPoints(): TurningPoint[] {
  const today = new Date();
  const offsets = [7, 18, 31, 46];
  return offsets.map((offset, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() + offset);
    return {
      date: formatDate(date),
      type: index % 2 === 0 ? "TOP" : "BOTTOM",
      strength: [82, 76, 88, 71][index],
    };
  });
}

export function buildDemoAnalysis(ticker: string): AnalystSummary {
  return {
    ticker,
    summary: `${ticker} is in demo mode with a constructive cycle bias and a near-term volatility window.`,
    cycle_explanation:
      "The composite cycle is rising from neutral territory while the projected segment remains positive. This favors waiting for confirmation rather than chasing extended candles.",
    turning_points_explanation:
      "The next detected top and bottom windows are close enough to matter for swing planning. Treat them as timing zones, not exact reversal promises.",
    scan_explanation:
      "Venus-Jupiter and Moon-Venus are the strongest demo combinations, with the best blend of correlation, lag, and directional accuracy.",
    outlook:
      "Bias is cautiously bullish while the composite line holds above zero. A break back below neutral would shift the playbook toward defensive positioning.",
  };
}
