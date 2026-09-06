import type { MarketOverviewResponse, OverviewIndexQuote, OverviewSector } from "../market-overview/types";

export type DataScreenTone = "up" | "down" | "flat" | "unavailable";

export type DataScreenModel = {
  status: MarketOverviewResponse["status"];
  asOf: string;
  observedAt: string;
  marketPhase: string;
  freshness: string;
  breadth: {
    rising: number | null;
    falling: number | null;
    flat: number | null;
    total: number | null;
    risingPercent: number | null;
  };
  limits: {
    up: number | null;
    down: number | null;
    broken: number | null;
    sealRate: number | null;
  };
  liquidity: {
    total: number | null;
    relative: number | null;
  };
  sentiment: { score: number | null; band: string; coverage: number | null };
  regime: { name: string; emotion: number | null; risk: number | null; heat: number | null; rotation: number | null };
  indices: Array<OverviewIndexQuote & { tone: DataScreenTone }>;
  minuteSeries: Array<{ observed_at: string; price: number | null; changePercent: number | null; volume: number | null }>;
  minuteSeriesByIndex: Record<string, Array<{ observed_at: string; price: number | null; changePercent: number | null; volume: number | null }>>;
  sectors: Array<OverviewSector & { tone: DataScreenTone; breadthPercent: number | null; leaderName: string | null }>;
  sectorFlows: Array<{ code: string; name: string; net: number | null; largeNet: number | null; superNet: number | null; delta: number | null; changePercent: number | null; tone: DataScreenTone; source: string; observed_at: string; samples: number }>;
  largeOrders: Array<{ symbol: string; name: string; net: number | null; direction: string; observed_at: string; quality: string }>;
  topStocks: Array<{ symbol: string; name: string; changePercent: number | null; volume: number | null; amount: number | null; volumeRatio: number | null; turnoverRate: number | null; marketCap: number | null; state: string; tone: DataScreenTone }>;
  anomalies: MarketOverviewResponse["anomalies"];
  liveFeed: MarketOverviewResponse["live_feed"];
  officialEvents: Array<{ event_id: string; event_date: string; event_type: string; code: string; name: string; kind: string; quality: string }>;
  dataScope: { marketQuotes: number | null; universe: number | null; stockSamples: number | null; sectorSamples: number | null; largeOrderSamples: number | null };
  coverage: { quoteCount: number | null; universeCount: number | null; percent: number | null; label: string };
  sources: string[];
};
