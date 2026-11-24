import type { MarketOverviewResponse } from "../market-overview/types";
import type { DataScreenModel, DataScreenTone } from "./types";

function numberOrNull(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function tone(value: string | number | null | undefined, quality?: string): DataScreenTone {
  if (quality === "unavailable") return "unavailable";
  const parsed = numberOrNull(value);
  if (parsed === null || parsed === 0) return "flat";
  return parsed > 0 ? "up" : "down";
}

function bounded<T>(items: T[], limit: number): T[] {
  return items.slice(0, limit);
}

function buildMinuteSeries(points: MarketOverviewResponse["minute_series"]): DataScreenModel["minuteSeries"] {
  return points.map((point, index, all) => {
    const price = numberOrNull(point.price);
    const first = numberOrNull(all[0]?.price);
    return {
      observed_at: point.observed_at,
      price,
      changePercent: price !== null && first ? (price / first - 1) * 100 : null,
      volume: numberOrNull(point.volume),
    };
  });
}

export function buildDataScreenModel(snapshot: MarketOverviewResponse | null): DataScreenModel {
  if (!snapshot) {
    return {
      status: "unavailable", asOf: "", observedAt: "", marketPhase: "unknown", freshness: "unavailable",
      breadth: { rising: null, falling: null, flat: null, total: null, risingPercent: null },
      limits: { up: null, down: null, broken: null, sealRate: null },
      liquidity: { total: null, relative: null }, sentiment: { score: null, band: "待确认", coverage: null },
      regime: { name: "待确认", emotion: null, risk: null, heat: null, rotation: null }, indices: [], minuteSeries: [], minuteSeriesByIndex: {}, sectors: [], sectorFlows: [], largeOrders: [], topStocks: [], anomalies: [], liveFeed: [], officialEvents: [],
      dataScope: { marketQuotes: null, universe: null, stockSamples: null, sectorSamples: null, largeOrderSamples: null },
      coverage: { quoteCount: null, universeCount: null, percent: null, label: "暂无有效行情" }, sources: [],
    };
  }
  const usable = snapshot.status !== "unavailable" && snapshot.market_data.quality !== "unavailable";
  const breadthTotal = usable
    ? snapshot.breadth.rising_count + snapshot.breadth.falling_count + snapshot.breadth.flat_count
    : null;
  const quoteCount = usable ? snapshot.market_data.quote_count : null;
  const universeCount = usable ? snapshot.market_data.universe_count : null;
  const coveragePercent = quoteCount !== null && universeCount ? quoteCount / universeCount * 100 : null;
  const indices = bounded(snapshot.indices, 5).map((item) => ({ ...item, tone: tone(item.change_percent, item.quality) }));
  const sectors = [...snapshot.sectors]
    .sort((left, right) => (numberOrNull(right.change_percent) ?? -Infinity) - (numberOrNull(left.change_percent) ?? -Infinity))
    .slice(0, 10)
    .map((item) => ({
      ...item,
      // Keep the provider's actual sector label. Shenwan is a separate
      // classification overlay and may legitimately be unverified.
      name: item.name || item.shenwan_industry?.name || "未命名板块",
      industry_system: item.industry_system ?? (item.shenwan_industry ? "申万" : "待核验"),
      tone: tone(item.change_percent),
      breadthPercent: item.stock_count ? item.rising_count / item.stock_count * 100 : null,
      leaderName: snapshot.sector_stocks[item.sector_id]?.[0]?.name ?? null,
    }));
  const minuteSeries = buildMinuteSeries(snapshot.minute_series).slice(-240);
  const minuteSeriesByIndex = Object.fromEntries(
    Object.entries(snapshot.minute_series_by_index ?? {}).map(([instrument, points]) => [
      instrument,
      buildMinuteSeries(points).slice(-240),
    ]),
  );
  if (!minuteSeriesByIndex["sh000001"] && minuteSeries.length) {
    minuteSeriesByIndex["sh000001"] = minuteSeries;
  }
  type SectorFlowPoint = NonNullable<MarketOverviewResponse["sector_fund_flow"]>[number];
  const sectorFlowGroups = new Map<string, SectorFlowPoint[]>();
  for (const item of snapshot.sector_fund_flow ?? []) {
    const current = sectorFlowGroups.get(item.sector_code) ?? [];
    current.push(item);
    sectorFlowGroups.set(item.sector_code, current);
  }
  const sectorChangeByKey = new Map<string, number>();
  for (const sector of snapshot.sectors) {
    const change = numberOrNull(sector.change_percent);
    if (change !== null) {
      sectorChangeByKey.set(sector.sector_id, change);
      sectorChangeByKey.set(sector.name, change);
    }
  }
  const sectorFlows = Array.from(sectorFlowGroups.entries())
    .map(([code, points]) => {
      const ordered = [...points].sort((left, right) => Date.parse(left.observed_at) - Date.parse(right.observed_at));
      const latest = ordered.at(-1);
      const previous = ordered.length > 1 ? ordered.at(-2) : undefined;
      const net = numberOrNull(latest?.main_net_yi);
      const previousNet = numberOrNull(previous?.main_net_yi);
      const sourceChangePercent = numberOrNull(latest?.change_percent);
      const catalogueChangePercent = sectorChangeByKey.get(code) ?? sectorChangeByKey.get(latest?.sector_name ?? "") ?? null;
      return {
        code,
        name: latest?.sector_name ?? code,
        net,
        largeNet: numberOrNull(latest?.large_net_yi),
        superNet: numberOrNull(latest?.super_net_yi),
        delta: net !== null && previousNet !== null ? net - previousNet : null,
        changePercent: sourceChangePercent ?? catalogueChangePercent,
        tone: tone(latest?.main_net_yi),
        source: latest?.source ?? "",
        observed_at: latest?.observed_at ?? "",
        samples: ordered.length,
      };
    })
    .sort((left, right) => Math.abs(right.net ?? 0) - Math.abs(left.net ?? 0)).slice(0, 12);
  const largeOrders = (snapshot.large_order_flows ?? [])
    .map((item) => ({ symbol: item.symbol, name: item.name, net: numberOrNull(item.main_net_yi), direction: item.direction, observed_at: item.observed_at, quality: item.quality }))
    .sort((left, right) => Math.abs(right.net ?? 0) - Math.abs(left.net ?? 0)).slice(0, 8);
  const topStocks = [...snapshot.market_stocks]
    .sort((left, right) => (numberOrNull(right.change_percent) ?? -Infinity) - (numberOrNull(left.change_percent) ?? -Infinity)).slice(0, 12)
    .map((item) => ({ symbol: item.symbol, name: item.name, changePercent: numberOrNull(item.change_percent), volume: numberOrNull(item.volume), amount: numberOrNull(item.amount_yi), volumeRatio: numberOrNull(item.volume_ratio), turnoverRate: numberOrNull(item.turnover_rate), marketCap: numberOrNull(item.market_cap_yi), state: item.state, tone: tone(item.change_percent, item.quality) }));
  return {
    status: snapshot.status, asOf: snapshot.as_of, observedAt: snapshot.observed_at,
    marketPhase: snapshot.market_data.phase ?? "unknown", freshness: snapshot.market_data.freshness ?? "unknown",
    breadth: {
      rising: usable ? snapshot.breadth.rising_count : null,
      falling: usable ? snapshot.breadth.falling_count : null,
      flat: usable ? snapshot.breadth.flat_count : null,
      total: breadthTotal,
      risingPercent: breadthTotal ? snapshot.breadth.rising_count / breadthTotal * 100 : null,
    },
    limits: {
      up: usable ? snapshot.limit_ecology.limit_up_count : null,
      down: usable ? snapshot.limit_ecology.limit_down_count : null,
      broken: usable ? snapshot.limit_ecology.broken_limit_up_count : null,
      sealRate: usable ? numberOrNull(snapshot.limit_ecology.seal_rate_percent) : null,
    },
    liquidity: {
      total: usable ? numberOrNull(snapshot.liquidity.total_amount_yi) : null,
      relative: usable ? numberOrNull(snapshot.liquidity.relative_amount) : null,
    },
    sentiment: { score: numberOrNull(snapshot.sentiment.score), band: snapshot.sentiment.band || "待确认", coverage: numberOrNull(snapshot.sentiment.coverage_percent) },
    regime: { name: snapshot.regime?.regime ?? "待确认", emotion: numberOrNull(snapshot.regime?.emotion_score), risk: numberOrNull(snapshot.regime?.risk_score), heat: numberOrNull(snapshot.regime?.heat_score), rotation: numberOrNull(snapshot.regime?.rotation_score) },
    indices, minuteSeries, minuteSeriesByIndex, sectors, sectorFlows, largeOrders, topStocks, anomalies: bounded(snapshot.anomalies, 8), liveFeed: bounded(snapshot.live_feed, 8),
    officialEvents: (snapshot.official_events ?? []).slice(0, 8).map((item) => ({ event_id: item.event_id, event_date: item.event_date, event_type: item.event_type, code: item.code, name: item.name, kind: item.kind, quality: item.quality })),
    dataScope: { marketQuotes: snapshot.data_scope?.market_quote_count ?? null, universe: snapshot.data_scope?.market_universe_count ?? null, stockSamples: snapshot.data_scope?.stock_sample_count ?? null, sectorSamples: snapshot.data_scope?.sector_sample_count ?? null, largeOrderSamples: snapshot.data_scope?.large_order_sample_count ?? null },
    coverage: {
      quoteCount, universeCount, percent: coveragePercent,
      label: coveragePercent === null ? "暂无有效行情" : `${coveragePercent.toFixed(1)}% 行情覆盖`,
    },
    sources: bounded(snapshot.sources, 6),
  };
}
