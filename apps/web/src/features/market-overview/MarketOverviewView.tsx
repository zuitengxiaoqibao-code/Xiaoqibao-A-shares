import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, CalendarDays, Clock3, Database, RefreshCw, Search } from "lucide-react";

import { MarketTemperatureGauge } from "./MarketTemperatureGauge";
import { MarketRegimeDashboard } from "./MarketRegimeDashboard";
import { MarketDataWatermarkCenter } from "./MarketDataWatermarkCenter";
import { OverviewFeatureRail } from "./OverviewFeatureRail";
import { numberedAnomalies, OverviewMinuteChart } from "./OverviewMinuteChart";
import { OverviewTables } from "./OverviewTables";
import type { MarketIntervalReviewLoader, MarketOverviewLoader, MarketOverviewResponse, OverviewIndexQuote } from "./types";
import { TerminalPageHeader } from "../../shared/terminal/TerminalPrimitives";
import { BreakingNewsStrip } from "../news-alerts/BreakingNewsStrip";
import type { BreakingNewsAlertLoader } from "../news-alerts/types";
import { useBreakingNewsAlerts } from "../news-alerts/useBreakingNewsAlerts";
import { safeStorageGet, safeStorageSet } from "../../shared/safeLocalStorage";
import { AnomalyVoiceAnnouncer } from "../speech/AnomalyVoiceAnnouncer";
import type { SpeechSynthesizer } from "../speech/types";
import { isAShareSymbol } from "../instrument-selection/SelectedInstrumentProvider";
import { DistinctMarketWorkspace } from "./workspaces/DistinctMarketWorkspace";
import { HomepageStartupOverlay } from "./HomepageStartupOverlay";
import { filterMarketOverviewTemporalData, isMarketOverviewSnapshotCurrent, readMarketOverviewCache, writeMarketOverviewCache } from "./marketOverviewCache";
import { formatOpeningCountdown, marketSessionDisplay } from "./marketSessionDisplay";
import { shanghaiDay } from "../../shared/tradingDayContext";
import { MetricBand } from "../../shared/visualization/VisualPrimitives";
import { EvidenceLedger } from "../../shared/evidence/EvidenceLedger";
import { FieldEvidenceDetails } from "../../shared/evidence/FieldEvidenceDetails";
import { SectorHeatmapPanel } from "../../shared/visualization/SectorHeatmapPanel";
import { featureDisplayLabel, featureMeta } from "./featureCatalog";
import { appendUniqueEntities, mergeEntitySnapshot, resolveIncrementalResponse } from "../../shared/incrementalResource";
import { loadWorkspaceState, updateWorkspaceFilter } from "../../shared/workspace/workspaceState";
import { SectionRefreshState } from "../../shared/SectionRefreshState";
import { useRealtimeFallback, useRealtimeState, useRealtimeSubscription } from "../../shared/realtime/RealtimeProvider";
import "./overview.css";

const expectedIndices = [
  ["sh000001", "上证指数"],
  ["sz399001", "深证成指"],
  ["sh000688", "科创50"],
  ["sz399006", "创业板指"],
  ["sh000905", "中证500"],
] as const;

const anomalyFeatures = new Set(["盘中异动", "异动语音播报", "竞价异动", "异动统计大全", "异动提醒", "个股异动"]);
const feedFeatures = new Set(["热点播报", "投资日历", "热点解读", "非研产业库", "开盘啦"]);

function timeLabel(value: string, withSeconds = false): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit", minute: "2-digit", second: withSeconds ? "2-digit" : undefined,
    hour12: false, timeZone: "Asia/Shanghai",
  }).format(new Date(value));
}

function signed(value: string | null, digits = 2): string {
  if (value === null) return "--";
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return `${number > 0 ? "+" : ""}${number.toFixed(digits)}`;
}

function direction(value: string | null): "up" | "down" | "flat" {
  const number = Number(value);
  if (!Number.isFinite(number) || number === 0) return "flat";
  return number > 0 ? "up" : "down";
}

function indexSlots(indices: OverviewIndexQuote[]) {
  return expectedIndices.map(([instrument, name]) => ({
    instrument, name, quote: indices.find((item) => item.instrument === instrument) ?? null,
  }));
}

function marketSourceLabel(source?: string): string {
  if (source === "tdx-local-rpc") return "本地通达信实时";
  if (source === "market-sentiment-cache") return "本地情绪快照";
  return "数据源准备中";
}

function finiteNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function keepAShareInformation(response: MarketOverviewResponse): MarketOverviewResponse {
  const liveFeed = response.live_feed
    .map((item) => ({ ...item, symbols: item.symbols.filter(isAShareSymbol) }))
    .filter((item) => item.symbols.length > 0);
  const anomalies = response.anomalies
    .map((item) => ({ ...item, symbols: item.symbols.filter(isAShareSymbol) }))
    .filter((item) => item.symbols.length > 0);
  return { ...response, live_feed: liveFeed, anomalies };
}

export function mergeStableAnomalySnapshot(
  current: MarketOverviewResponse | null,
  incoming: MarketOverviewResponse,
): MarketOverviewResponse {
  return resolveIncrementalResponse(current, incoming, {
    tradeDate: (value) => value.as_of,
    observedAt: (value) => value.observed_at,
    isEmpty: (value) => value.market_data.quote_count === 0 && value.market_stocks.length === 0 && value.indices.length === 0,
    merge: (previous, next) => {
      const mergeTemporalData = next.market_data.phase === undefined
        || ((next.market_data.phase === "intraday" || next.market_data.phase === "postclose")
          && next.market_data.freshness !== "previous_close");
      return {
        ...next,
        anomalies: mergeTemporalData
          ? appendUniqueEntities(previous.anomalies, next.anomalies, (item) => item.anomaly_id)
          : next.anomalies,
        live_feed: mergeTemporalData
          ? appendUniqueEntities(previous.live_feed, next.live_feed, (item) => item.event_id)
          : next.live_feed,
        minute_series: mergeTemporalData
          ? mergeEntitySnapshot(previous.minute_series, next.minute_series, (item) => item.observed_at)
          : next.minute_series,
        market_stocks: mergeEntitySnapshot(previous.market_stocks, next.market_stocks, (item) => item.symbol),
      };
    },
  });
}

function defaultWorkspaceForSnapshot(response: MarketOverviewResponse): string {
  const { phase, freshness } = response.market_data;
  if (phase === "premarket" || freshness === "previous_close") return "盘中异动";
  if (phase === "postclose" || phase === "closed" || freshness === "final") return "复盘统计大全";
  if (phase === "intraday") return response.anomalies.length > 0 ? "盘中异动" : "情绪周期";
  if (freshness === "stale" || freshness === "unavailable") return "情绪周期";
  return response.anomalies.length > 0 ? "盘中异动" : "情绪周期";
}

const MARKET_OVERVIEW_FEATURE_KEY = "qibao-market-overview-feature";

function storedWorkspace(): string | null {
  const legacy = safeStorageGet(MARKET_OVERVIEW_FEATURE_KEY, "");
  const restored = loadWorkspaceState()?.filters["market-overview"]?.activeFeature;
  const stored = legacy || (typeof restored === "string" ? restored : "");
  return featureMeta[stored as keyof typeof featureMeta] ? stored : null;
}

export function MarketOverviewView({ load, loadAlerts, onOpenAShare, onOpenCompanyResearch, onOpenQuantAnalysis, synthesizeSpeech, loadIntervalReview }: {
  load: MarketOverviewLoader;
  loadAlerts?: BreakingNewsAlertLoader;
  onOpenAShare?: (symbol: string) => void;
  onOpenCompanyResearch?: (symbol: string) => void;
  onOpenQuantAnalysis?: (symbol: string) => void;
  synthesizeSpeech?: SpeechSynthesizer;
  loadIntervalReview?: MarketIntervalReviewLoader;
}) {
  const [initialCache] = useState(() => readMarketOverviewCache());
  const [data, setData] = useState<MarketOverviewResponse | null>(initialCache?.value ?? null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasCompletedInitialLoad, setHasCompletedInitialLoad] = useState(false);
  const [cacheTimestamp, setCacheTimestamp] = useState<string | null>(initialCache?.cachedAt ?? null);
  const [usingCache, setUsingCache] = useState(() => Boolean(initialCache));
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [clockNow, setClockNow] = useState(() => new Date());
  const [visible, setVisible] = useState(document.visibilityState !== "hidden");
  const [storedFeature] = useState(storedWorkspace);
  const [activeFeature, setActiveFeature] = useState(storedFeature ?? "盘中异动");
  const [selectedAnomalyId, setSelectedAnomalyId] = useState<string | null>(null);
  const [selectedSectorId, setSelectedSectorId] = useState<string | null>(null);
  const [searchSymbol, setSearchSymbol] = useState("");
  const requestRef = useRef<AbortController | null>(null);
  const hasAppliedDefaultFeatureRef = useRef(Boolean(storedFeature));
  const userSelectedFeatureRef = useRef(Boolean(storedFeature));
  const openingRefreshDayRef = useRef<string | null>(null);
  const dataRef = useRef<MarketOverviewResponse | null>(data);
  dataRef.current = data;
  const realtimeState = useRealtimeState();
  const realtimeFallback = useRealtimeFallback();
  const alertState = useBreakingNewsAlerts(loadAlerts, undefined, 6);
  const aShareAlertState = useMemo(() => ({
    ...alertState,
    alerts: alertState.alerts.filter((alert) => alert.affected_symbols.some(isAShareSymbol)),
  }), [alertState]);

  const applyIncoming = useCallback((raw: MarketOverviewResponse) => {
    const temporalReference = raw.market_data.phase === undefined
      ? new Date(raw.observed_at)
      : new Date();
    const incoming = keepAShareInformation(
      filterMarketOverviewTemporalData(raw, shanghaiDay(temporalReference)),
    );
    const next = mergeStableAnomalySnapshot(dataRef.current, incoming);
    setData(next);
    if (next.status !== "unavailable" && next.market_data.quality !== "unavailable") {
      setHasCompletedInitialLoad(true);
    }
    const stored = writeMarketOverviewCache(next);
    setCacheTimestamp((current) => stored.persisted ? stored.cachedAt : current);
    setUsingCache(false);
    setError(null);
    setSelectedAnomalyId((current) => current && next.anomalies.some((item) => item.anomaly_id === current) ? current : null);
    setSelectedSectorId((current) => current && next.sectors.some((item) => item.sector_id === current) ? current : next.sectors[0]?.sector_id ?? null);
  }, []);

  const refresh = useCallback(async () => {
    if (requestRef.current !== null) return;
    const controller = new AbortController();
    requestRef.current = controller;
    if (dataRef.current === null) setLoading(true);
    try {
      const incoming = await load(controller.signal);
      if (controller.signal.aborted) return;
      applyIncoming(incoming);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      if (!controller.signal.aborted) {
        setError(reason instanceof Error ? reason.message : "信息总览数据暂不可用");
        if (dataRef.current && !isMarketOverviewSnapshotCurrent(dataRef.current)) {
          setData(null);
          setCacheTimestamp(null);
          setUsingCache(false);
        } else {
          setUsingCache(true);
        }
      }
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
        if (!controller.signal.aborted) setLoading(false);
      }
    }
  }, [applyIncoming, load]);

  useEffect(() => {
    void refresh();
    return () => {
      requestRef.current?.abort();
      requestRef.current = null;
    };
  }, [refresh]);

  useRealtimeSubscription<MarketOverviewResponse>("market_overview", (event) => applyIncoming(event.payload));

  useEffect(() => {
    const onVisibility = () => setVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setClockNow(new Date()), 1_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!autoRefresh || !visible) return;
    const timer = window.setInterval(() => void refresh(), 5_000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, refresh, visible]);

  useEffect(() => {
    if (
      hasAppliedDefaultFeatureRef.current
      || userSelectedFeatureRef.current
      || !data
      || data.status === "unavailable"
      || data.market_data.quality === "unavailable"
    ) return;
    setActiveFeature(defaultWorkspaceForSnapshot(data));
    hasAppliedDefaultFeatureRef.current = true;
  }, [data]);

  const selectFeature = (feature: string) => {
    userSelectedFeatureRef.current = true;
    hasAppliedDefaultFeatureRef.current = true;
    setActiveFeature(feature);
    safeStorageSet(MARKET_OVERVIEW_FEATURE_KEY, feature);
    updateWorkspaceFilter("market-overview", { activeFeature: feature });
  };

  const focusedRegion = anomalyFeatures.has(activeFeature)
    ? "anomalies"
    : feedFeatures.has(activeFeature) ? "feed" : "sectors";
  const displayNow = data?.market_data.phase === undefined && data?.observed_at
    ? new Date(data.observed_at)
    : clockNow;
  const displayDay = shanghaiDay(displayNow);
  const temporalData = useMemo(
    () => data ? filterMarketOverviewTemporalData(data, displayDay) : null,
    [data, displayDay],
  );
  const session = marketSessionDisplay({
    now: displayNow,
    phase: data?.market_data.phase,
    points: temporalData?.minute_series ?? [],
  });
  const sessionAnomalies = temporalData?.anomalies ?? [];
  const sessionLiveFeed = temporalData?.live_feed ?? [];
  const showMinuteChart = (session.stage === "live" || session.stage === "postclose")
    && (temporalData?.minute_series.length ?? 0) > 0;
  const slots = useMemo(() => indexSlots(data?.indices ?? []), [data?.indices]);
  const numberedAnomalyItems = useMemo(() => numberedAnomalies(sessionAnomalies), [sessionAnomalies]);
  const selectedAnomaly = sessionAnomalies.find((item) => item.anomaly_id === selectedAnomalyId) ?? null;
  const effectiveSelectedAnomaly = selectedAnomaly ?? numberedAnomalyItems[0]?.event ?? null;
  const effectiveSelectedAnomalyId = effectiveSelectedAnomaly?.anomaly_id ?? null;
  const marketData = data?.market_data;
  const freshness = marketData?.freshness && marketData.freshness !== "unknown"
    ? marketData.freshness
    : marketData?.quality === "unavailable" ? "unavailable" : "live";
  const snapshotReady = Boolean(
    data
    && data.status !== "unavailable"
    && marketData?.quality !== "unavailable"
    && !usingCache
    && !loading
    && !error
  );
  const liveReady = snapshotReady && freshness === "live";

  useEffect(() => {
    if (session.stage !== "awaiting_first_tick" || openingRefreshDayRef.current === displayDay) return;
    openingRefreshDayRef.current = displayDay;
    void refresh();
  }, [displayDay, refresh, session.stage]);

  const statusLabel = data && loading
    ? "正在更新最新数据"
    : !data && loading
    ? "正在聚合 A 股市场数据"
    : error && !data ? "数据链路中断"
    : freshness === "previous_close" ? "上一交易日数据可用"
    : freshness === "final" ? "当日收盘数据可用"
    : freshness === "stale" ? "历史快照可用"
    : data?.status === "ready" ? "实时数据就绪"
    : data?.status === "partial" ? "部分数据可用"
    : "当前数据不可用";
  const headerStatusLabel = data && loading
    ? "正在更新最新数据"
    : error && data
    ? "最新数据更新失败 · 继续使用缓存"
    : snapshotReady && freshness === "previous_close"
    ? "已加载上一交易日快照 · 等待开盘"
    : snapshotReady && freshness === "final"
    ? "已加载收盘数据 · 等待下一交易日"
    : snapshotReady && freshness === "stale"
    ? "已加载历史快照 · 等待最新数据"
    : snapshotReady && liveReady
    ? "已加载最新数据 · 实时监控中"
    : statusLabel;
  const coverage = marketData
    ? `${marketData.quote_count.toLocaleString("zh-CN")} / ${marketData.universe_count.toLocaleString("zh-CN")}`
    : "-- / --";
  const hasVerifiedMarket = Boolean(data && data.status !== "unavailable" && marketData?.quality !== "unavailable");
  const metricNumber = (value: string | number | null | undefined): number | null => hasVerifiedMarket ? finiteNumber(value) : null;
  const metricPercent = (value: string | number | null | undefined): string | null => {
    const parsed = metricNumber(value);
    return parsed === null ? null : `${parsed.toFixed(1)}%`;
  };
  const breadthTotal = data ? data.breadth.rising_count + data.breadth.falling_count + data.breadth.flat_count : 0;
  const risingRatio = hasVerifiedMarket && breadthTotal > 0 ? (data?.breadth.rising_count ?? 0) / breadthTotal * 100 : null;
  const metricDetail = hasVerifiedMarket
    ? freshness === "previous_close" ? "上一交易日快照"
    : freshness === "final" ? "收盘最终快照"
    : freshness === "stale" ? "历史快照"
    : data?.status === "ready" ? "实时快照" : "部分快照"
    : "等待可用证据";

  const openSearchedSymbol = () => {
    const symbol = searchSymbol.trim();
    if (isAShareSymbol(symbol)) onOpenAShare?.(symbol);
  };

  return <main className="terminal-page market-overview-page">
    <HomepageStartupOverlay
      data={data}
      error={error}
      loading={loading}
      liveReady={liveReady}
      snapshotReady={snapshotReady}
      hasCompletedInitialLoad={hasCompletedInitialLoad}
      onRetry={() => void refresh()}
    />
    <TerminalPageHeader
      className="overview-terminal-header"
      eyebrow="A-SHARE / MARKET OVERVIEW"
      title="信息总览"
      description="A 股全市场行情、情绪、异动、题材与关联资讯同屏监测"
      actions={<div className={`overview-status ${data?.status ?? "unavailable"}`} data-refreshing={loading ? "true" : "false"}>
        <Activity size={15} />
        <span><b>{headerStatusLabel}</b><small>{data ? `${coverage} 行情覆盖` : "等待首次快照"}</small></span>
      </div>}
    />
    <div className="overview-sr-only" role="status">{statusLabel}</div>

    {error && data
      ? <SectionRefreshState state="stale" phase="信息总览最新数据刷新" error={error} onRetry={() => void refresh()} />
      : error && <div className="overview-error"><AlertTriangle size={15} /><span>{error}</span></div>}

    <section className="overview-market-strip" aria-label="A 股市场情绪与核心指数">
      <MarketTemperatureGauge sentiment={data?.sentiment ?? { score: null, band: "等待数据", coverage_percent: "0", quality: "unavailable", observed_at: new Date().toISOString() }} />
      <MetricBand items={[
        { label: "封板率", value: metricPercent(data?.limit_ecology.seal_rate_percent), tone: hasVerifiedMarket ? "up" : "unavailable", detail: metricDetail },
        { label: "上涨占比", value: risingRatio === null ? null : `${risingRatio.toFixed(1)}%`, tone: hasVerifiedMarket ? "up" : "unavailable", detail: metricDetail },
        { label: "成交热度", value: metricNumber(data?.liquidity.relative_amount), tone: hasVerifiedMarket ? "live" : "unavailable", detail: hasVerifiedMarket ? "相对 20 日基准" : metricDetail },
        { label: "情绪分", value: metricNumber(data?.sentiment.score), tone: hasVerifiedMarket && data?.sentiment.quality === "ready" ? "warning" : "unavailable", detail: hasVerifiedMarket ? data?.sentiment.band ?? "已读取" : metricDetail },
        { label: "行情覆盖", value: marketData && marketData.universe_count > 0 && hasVerifiedMarket ? `${(marketData.quote_count / marketData.universe_count * 100).toFixed(1)}%` : null, tone: hasVerifiedMarket ? "live" : "unavailable", detail: marketData ? `${coverage} 条` : metricDetail },
      ]} />
      <div className="overview-stat"><span>涨停 / 炸板</span><b className="up">{data ? `${data.limit_ecology.limit_up_count} / ${data.limit_ecology.broken_limit_up_count}` : "-- / --"}</b><small className="down">跌停 {data?.limit_ecology.limit_down_count ?? "--"}</small></div>
      <div className="overview-stat"><span>A 股涨跌广度</span><b className="up">上涨 {data?.breadth.rising_count ?? "--"}</b><small className="down">下跌 {data?.breadth.falling_count ?? "--"}</small></div>
      <div className="overview-stat"><span>封板率</span><b>{data?.limit_ecology.seal_rate_percent ? `${data.limit_ecology.seal_rate_percent}%` : "--"}</b><small>炸板 {data?.limit_ecology.broken_limit_up_count ?? "--"}</small></div>
      <div className="overview-stat liquidity"><span>两市成交</span><b>{data?.liquidity.total_amount_yi ? `${data.liquidity.total_amount_yi}亿` : "--"}</b><small>相对基准 {data?.liquidity.relative_amount ?? "--"}</small></div>
      <div className="overview-index-strip">
        {slots.map(({ instrument, name, quote }) => <div key={instrument}>
          <span>{name}</span><b>{quote?.value ?? "--"}</b>
          <small className={direction(quote?.change_percent ?? null)}>{quote ? `${signed(quote.change)}  ${signed(quote.change_percent)}%` : "数据暂缺"}</small>
        </div>)}
      </div>
      <aside className="overview-top-controls" aria-label="总览查询与数据状态">
        <div className="overview-search-box">
          <Search size={15} />
          <input
            type="search"
            aria-label="搜索股票代码"
            inputMode="numeric"
            maxLength={6}
            placeholder="搜索代码"
            value={searchSymbol}
            onChange={(event) => setSearchSymbol(event.target.value.replace(/\D/g, ""))}
            onKeyDown={(event) => { if (event.key === "Enter") openSearchedSymbol(); }}
          />
          <button type="button" onClick={openSearchedSymbol} disabled={!isAShareSymbol(searchSymbol)} aria-label="打开股票">查看</button>
        </div>
        <div className="overview-source-row"><Database size={14} /><span><b>{marketSourceLabel(marketData?.source)}</b><small>{coverage}</small></span></div>
        <div className="overview-source-row"><CalendarDays size={14} /><span><b>{data?.as_of ?? "--"}</b><small>{statusLabel}</small></span></div>
      </aside>
    </section>

    {data?.review?.watermark && <MarketDataWatermarkCenter watermark={data.review.watermark} />}
    {((data?.field_evidence?.length ?? 0) > 0 || (data?.review?.evidence_ledger?.length ?? 0) > 0) && <div className="overview-evidence-summary-row" role="group" aria-label="数据真实性与证据摘要">
      {(data?.field_evidence?.length ?? 0) > 0 && <FieldEvidenceDetails entries={data!.field_evidence!} />}
      {(data?.review?.evidence_ledger?.length ?? 0) > 0 && <EvidenceLedger entries={data!.review!.evidence_ledger!} />}
    </div>}

    {loadAlerts && <BreakingNewsStrip {...aShareAlertState} onOpenAShare={onOpenAShare} />}

    <OverviewFeatureRail active={activeFeature} onSelect={selectFeature} />

    <div className="overview-toolbar">
      <button type="button" aria-label="立即刷新" disabled={loading} onClick={() => void refresh()}><RefreshCw size={14} className={loading ? "spinning" : ""} />刷新</button>
      <label><input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} />自动刷新</label>
      <span>{realtimeState === "connected" ? "实时推送已连接" : `HTTP 保底 · ${realtimeFallback ? 15 : 60} 秒`}</span>
      <span>当前筛选 <strong>{featureDisplayLabel(activeFeature)}</strong></span>
      {!visible && <span className="overview-paused">页面隐藏，刷新已暂停</span>}
      {data && <time dateTime={data.observed_at}>最新观测 {timeLabel(data.observed_at, true)}{usingCache && cacheTimestamp ? ` · 缓存 ${timeLabel(cacheTimestamp, true)}` : ""}</time>}
    </div>

    {activeFeature === "盘中异动" && <><section className="overview-workspace">
      <section className={`overview-chart-panel ${focusedRegion === "anomalies" ? "focused" : ""}`} aria-label="上证指数分时与异动">
        <header><div><b>上证指数分时</b><span>价格 / 成交量 / 稳定事件标记</span></div>{effectiveSelectedAnomaly && <strong>{effectiveSelectedAnomaly.label}</strong>}</header>
        {effectiveSelectedAnomaly && <section className="overview-selected-anomaly" aria-label="当前异动摘要" data-direction={effectiveSelectedAnomaly.direction}>
          <div><small>{timeLabel(effectiveSelectedAnomaly.occurred_at)} · {effectiveSelectedAnomaly.direction === "positive" ? "正向异动" : effectiveSelectedAnomaly.direction === "negative" ? "负向异动" : effectiveSelectedAnomaly.direction === "uncertain" ? "影响待核验" : "中性异动"}</small><strong>{effectiveSelectedAnomaly.headline}</strong></div>
          <div>{effectiveSelectedAnomaly.themes.length ? effectiveSelectedAnomaly.themes.slice(0, 3).map((theme) => <em key={theme}>{theme}</em>) : <em>无题材标签</em>}</div>
        </section>}
        <div className="overview-chart-shell">{showMinuteChart
          ? <OverviewMinuteChart points={temporalData?.minute_series ?? []} anomalies={sessionAnomalies} selectedAnomalyId={effectiveSelectedAnomalyId} />
          : <div className="overview-market-wait" data-stage={session.stage} role="status">
              <span className="overview-market-wait-pulse" aria-hidden="true" />
              <small>{session.stage === "waiting_open" || session.stage === "call_auction" ? "距离 09:30 开盘" : "A 股实时行情"}</small>
              <strong>{session.title}</strong>
              {(session.stage === "waiting_open" || session.stage === "call_auction")
                && <time dateTime={`PT${session.secondsToOpen}S`}>{formatOpeningCountdown(session.secondsToOpen)}</time>}
              <p>{session.detail}</p>
            </div>}
        </div>
      </section>

      <section className={`overview-anomaly-panel ${focusedRegion === "anomalies" ? "focused" : ""}`} aria-label="异动记录">
        <header><b>异动记录</b><span>{sessionAnomalies.length} 条</span></header>
        <div className="overview-anomaly-list">{sessionAnomalies.length === 0
          ? <p className="overview-empty">{session.stage === "waiting_open" || session.stage === "call_auction" ? "等待开盘后接收今日异动" : session.stage === "closed" ? "今日休市，无盘中异动" : "正在监控今日已验证异动"}</p>
          : numberedAnomalyItems.map(({ event: item, number }) => <button
            key={item.anomaly_id} type="button" aria-pressed={effectiveSelectedAnomalyId === item.anomaly_id}
            aria-label={`${timeLabel(item.occurred_at)} ${item.label}`}
            onClick={() => setSelectedAnomalyId(item.anomaly_id)}
          ><span className="overview-anomaly-number" data-direction={item.direction}>{number}</span><time>{timeLabel(item.occurred_at)}</time><span><b>{item.label}</b><small>{item.headline}</small></span></button>)}</div>
      </section>

      <section className={`overview-feed-panel ${focusedRegion === "feed" ? "focused" : ""}`} aria-label="A 股关联资讯">
        <header><div><b>A 股关联资讯</b><span>仅保留已关联 A 股的公开来源</span></div><Activity size={15} /></header>
        <div className="overview-feed-list">{sessionLiveFeed.length === 0
          ? <p className="overview-empty">{session.stage === "waiting_open" || session.stage === "call_auction" ? "等待开盘后接收今日关联资讯" : session.stage === "closed" ? "今日休市，暂不关联盘中资讯" : "正在接收今日 A 股关联资讯"}</p>
          : sessionLiveFeed.map((item) => <article key={item.event_id}>
            <time><Clock3 size={12} />{timeLabel(item.occurred_at)}</time><h2>{item.headline}</h2>
            {item.summary && <p>{item.summary}</p>}
            <div>{item.themes.map((theme) => <span key={theme}>{theme}</span>)}<small>{item.source}</small></div>
          </article>)}</div>
      </section>
    </section>

    <div className={focusedRegion === "sectors" ? "overview-tables-focused" : ""}>
      <SectorHeatmapPanel sectors={data?.sectors ?? []} selectedSectorId={selectedSectorId} onSelectSector={setSelectedSectorId} />
      <OverviewTables sectors={data?.sectors ?? []} sectorStocks={data?.sector_stocks ?? {}} selectedSectorId={selectedSectorId} onSelectSector={setSelectedSectorId} onOpenAShare={onOpenAShare} />
    </div></>}

    {activeFeature === "情绪周期" && data?.regime_metrics && data.regime
      ? <MarketRegimeDashboard metrics={data.regime_metrics} regime={data.regime} />
      : activeFeature === "异动语音播报" && synthesizeSpeech
        ? <AnomalyVoiceAnnouncer anomalies={data?.anomalies ?? []} synthesize={synthesizeSpeech} />
        : activeFeature !== "盘中异动" && data && <DistinctMarketWorkspace feature={activeFeature} data={data} onOpenAShare={onOpenAShare} onOpenCompanyResearch={onOpenCompanyResearch} onOpenQuantAnalysis={onOpenQuantAnalysis} loadIntervalReview={loadIntervalReview} />}

    <footer className="overview-footnote">
      <span>来源：{data?.sources.join(" / ") || "等待数据"}</span>
      {data?.warnings.map((warning) => <span key={warning}><AlertTriangle size={12} />{warning}</span>)}
      <small>仅作信息观察，不构成投资建议</small>
    </footer>
  </main>;
}
