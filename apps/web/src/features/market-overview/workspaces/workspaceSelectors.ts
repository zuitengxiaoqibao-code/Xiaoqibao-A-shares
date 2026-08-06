import type {
  MarketOverviewResponse,
  OverviewAnomaly,
  OverviewFeatureStock,
  OverviewLiveFeedItem,
  OverviewSector,
} from "../types";

export type DerivedStock = OverviewFeatureStock & {
  change: number | null;
  amount: number | null;
  gap: number | null;
  amplitude: number | null;
  closePosition: number | null;
  highPullback: number | null;
  attentionScore: number | null;
  themes: string[];
};

export type DerivedSector = OverviewSector & {
  change: number | null;
  amount: number | null;
  breadthPercent: number | null;
  limitDensityPercent: number | null;
  strengthScore: number | null;
};

export type DerivedTheme = {
  name: string;
  evidenceCount: number;
  newsCount: number;
  anomalyCount: number;
  symbols: string[];
  latestAt: string;
};

export type WorkspaceMarketModel = {
  stocks: DerivedStock[];
  sectors: DerivedSector[];
  themes: DerivedTheme[];
  news: OverviewLiveFeedItem[];
  anomalies: OverviewAnomaly[];
};

export function numberValue(value: string | number | null | undefined): number | null {
  const parsed = Number(value);
  return value === null || value === undefined || value === "" || !Number.isFinite(parsed) ? null : parsed;
}

export function signedPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function optionalValue(value: string | number | null | undefined, suffix = ""): string {
  const parsed = numberValue(value);
  return parsed === null ? "--" : `${parsed}${suffix}`;
}

function compareNullableDesc(a: number | null, b: number | null): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return b - a;
}

function compareNullableAsc(a: number | null, b: number | null): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return a - b;
}

function themesBySymbol(data: MarketOverviewResponse): Map<string, Set<string>> {
  const result = new Map<string, Set<string>>();
  const append = (symbol: string, themes: string[]) => {
    const current = result.get(symbol) ?? new Set<string>();
    themes.forEach((theme) => current.add(theme));
    result.set(symbol, current);
  };
  data.live_feed.forEach((item) => item.symbols.forEach((symbol) => append(symbol, item.themes)));
  data.anomalies.forEach((item) => item.symbols.forEach((symbol) => append(symbol, item.themes)));
  return result;
}

function deriveStocks(data: MarketOverviewResponse): DerivedStock[] {
  const symbolThemes = themesBySymbol(data);
  return (data.market_stocks ?? []).map((stock) => {
    const previous = numberValue(stock.previous_close);
    const open = numberValue(stock.open);
    const high = numberValue(stock.high);
    const low = numberValue(stock.low);
    const price = numberValue(stock.price);
    const change = numberValue(stock.change_percent);
    const amount = numberValue(stock.amount_yi);
    const gap = previous !== null && previous > 0 && open !== null ? (open / previous - 1) * 100 : null;
    const amplitude = previous !== null && previous > 0 && high !== null && low !== null ? (high - low) / previous * 100 : null;
    const closePosition = high !== null && low !== null && price !== null && high > low ? (price - low) / (high - low) * 100 : null;
    const highPullback = high !== null && high > 0 && price !== null ? (price / high - 1) * 100 : null;
    const themes = [...(symbolThemes.get(stock.symbol) ?? [])];
    const attentionScore = change !== null && amount !== null
      ? Math.max(0, Math.min(100,
        35 + Math.abs(change) * 2 + Math.min(20, Math.log10(Math.max(0, amount) + 1) * 10) + Math.min(15, themes.length * 5),
      ))
      : null;
    return { ...stock, change, amount, gap, amplitude, closePosition, highPullback, attentionScore, themes };
  });
}

function deriveSectors(data: MarketOverviewResponse): DerivedSector[] {
  return data.sectors.map((sector) => {
    const change = numberValue(sector.change_percent);
    const amount = numberValue(sector.amount_yi);
    const breadthBase = sector.rising_count + sector.falling_count;
    const breadthPercent = breadthBase > 0 ? sector.rising_count / breadthBase * 100 : null;
    const limitDensityPercent = sector.stock_count > 0 ? sector.limit_up_count / sector.stock_count * 100 : null;
    const strengthScore = change !== null && breadthPercent !== null && limitDensityPercent !== null
      ? Math.max(0, Math.min(100,
        30 + change * 6 + (breadthPercent - 50) * 0.45 + Math.min(20, limitDensityPercent * 4),
      ))
      : null;
    return { ...sector, change, amount, breadthPercent, limitDensityPercent, strengthScore };
  }).sort((a, b) => compareNullableDesc(a.strengthScore, b.strengthScore));
}

function deriveThemes(data: MarketOverviewResponse): DerivedTheme[] {
  const map = new Map<string, DerivedTheme>();
  const add = (name: string, symbols: string[], occurredAt: string, kind: "news" | "anomaly") => {
    const existing = map.get(name) ?? {
      name, evidenceCount: 0, newsCount: 0, anomalyCount: 0, symbols: [], latestAt: occurredAt,
    };
    existing.evidenceCount += 1;
    existing.newsCount += kind === "news" ? 1 : 0;
    existing.anomalyCount += kind === "anomaly" ? 1 : 0;
    existing.symbols = [...new Set([...existing.symbols, ...symbols])];
    if (new Date(occurredAt).getTime() > new Date(existing.latestAt).getTime()) existing.latestAt = occurredAt;
    map.set(name, existing);
  };
  data.live_feed.forEach((item) => item.themes.forEach((theme) => add(theme, item.symbols, item.occurred_at, "news")));
  data.anomalies.forEach((item) => item.themes.forEach((theme) => add(theme, item.symbols, item.occurred_at, "anomaly")));
  return [...map.values()].sort((a, b) => b.evidenceCount - a.evidenceCount || b.symbols.length - a.symbols.length);
}

export function buildWorkspaceMarketModel(data: MarketOverviewResponse): WorkspaceMarketModel {
  return {
    stocks: deriveStocks(data),
    sectors: deriveSectors(data),
    themes: deriveThemes(data),
    news: [...data.live_feed].sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()),
    anomalies: [...data.anomalies].sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()),
  };
}

export function stocksForVariant(model: WorkspaceMarketModel, variant: string): DerivedStock[] {
  const stocks = [...model.stocks];
  if (["strict-limit", "sector-limit"].includes(variant)) return stocks.filter((item) => item.state === "limit_up" && item.amount !== null).sort((a, b) => compareNullableDesc(a.amount, b.amount));
  if (["strict-broken", "drawdown"].includes(variant)) return stocks.filter((item) => item.state === "broken_limit_up" && item.highPullback !== null).sort((a, b) => compareNullableAsc(a.highPullback, b.highPullback));
  if (["strict-down", "risk-balance"].includes(variant)) return stocks.filter((item) => item.state === "limit_down" && item.change !== null).sort((a, b) => compareNullableAsc(a.change, b.change));
  if (["verified-only", "previous-only", "interval-return"].includes(variant)) return [];
  if (["gap-strength", "overnight"].includes(variant)) return stocks.filter((item) => item.gap !== null && item.gap >= 1).sort((a, b) => compareNullableDesc(a.gap, b.gap) || compareNullableDesc(a.change, b.change));
  if (variant === "seal-gap") return stocks.filter((item) => item.state === "limit_up" || (item.gap !== null && item.gap >= 3)).sort((a, b) => compareNullableDesc(a.gap, b.gap) || compareNullableDesc(a.change, b.change));
  if (variant === "positive-negative") return stocks.filter((item) => item.gap !== null && Math.abs(item.gap) >= 1).sort((a, b) => compareNullableDesc(a.gap === null ? null : Math.abs(a.gap), b.gap === null ? null : Math.abs(b.gap)) || compareNullableDesc(a.amount, b.amount));
  if (variant === "seal-watch") return stocks.filter((item) => item.state === "limit_up" || (item.gap !== null && item.gap >= 3 && item.change !== null && item.change >= 5)).sort((a, b) => compareNullableDesc(a.change, b.change) || compareNullableDesc(a.gap, b.gap));
  if (variant === "auction-pass") return stocks.filter((item) => item.gap !== null && item.change !== null && item.closePosition !== null && item.amount !== null && item.gap >= -1 && item.gap <= 4 && item.change >= item.gap - 1 && item.closePosition >= 50 && item.amount > 0).sort((a, b) => compareNullableDesc(a.change, b.change));
  if (variant === "opening-first") return stocks.filter((item) => item.gap !== null && item.amount !== null && Math.abs(item.gap) >= 1).sort((a, b) => compareNullableDesc(a.amount, b.amount) || compareNullableDesc(a.gap === null ? null : Math.abs(a.gap), b.gap === null ? null : Math.abs(b.gap)));
  if (variant === "gap-vs-now") return stocks.filter((item) => item.gap !== null && Math.abs(item.gap) >= 1).sort((a, b) => compareNullableDesc(a.gap === null ? null : Math.abs(a.gap), b.gap === null ? null : Math.abs(b.gap)));
  if (variant === "amplitude-change") return stocks.filter((item) => item.amplitude !== null && item.change !== null && item.amplitude >= 4).sort((a, b) => compareNullableDesc(a.amplitude, b.amplitude) || compareNullableDesc(a.change === null ? null : Math.abs(a.change), b.change === null ? null : Math.abs(b.change)));
  if (variant === "anomaly-score") return stocks.filter((item) => (item.amplitude !== null && item.amplitude >= 5) || (item.gap !== null && Math.abs(item.gap) >= 2) || (item.change !== null && Math.abs(item.change) >= 3)).sort((a, b) => compareNullableDesc(a.attentionScore, b.attentionScore));
  if (["amount-only", "activity-not-seat"].includes(variant)) return stocks.filter((item) => item.amount !== null).sort((a, b) => compareNullableDesc(a.amount, b.amount));
  if (["theme-count", "theme-members", "theme-confirm", "discovery-stocks", "industry-stocks"].includes(variant)) return stocks.sort((a, b) => b.themes.length - a.themes.length || compareNullableDesc(a.change, b.change));
  if (["attention-score", "cross-rank"].includes(variant)) return stocks.filter((item) => item.attentionScore !== null).sort((a, b) => compareNullableDesc(a.attentionScore, b.attentionScore));
  if (variant === "evidence-score") return stocks.filter((item) => item.themes.length > 0 && item.change !== null && item.change > -2 && item.state !== "limit_down" && item.attentionScore !== null).sort((a, b) => compareNullableDesc(a.attentionScore, b.attentionScore));
  if (variant === "rule-result") return stocks.filter((item) => item.change !== null && item.closePosition !== null && item.amount !== null && item.change >= -1.5 && item.change <= 5 && item.closePosition >= 60 && item.amount > 0 && item.state === "active").sort((a, b) => compareNullableDesc(a.closePosition, b.closePosition) || compareNullableDesc(a.amount, b.amount));
  return stocks.sort((a, b) => compareNullableDesc(a.change, b.change) || compareNullableDesc(a.amount, b.amount));
}
