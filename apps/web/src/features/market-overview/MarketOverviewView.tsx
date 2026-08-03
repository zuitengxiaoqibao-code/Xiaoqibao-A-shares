import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, CalendarDays, Clock3, Database, RefreshCw, Search } from "lucide-react";

import { MarketTemperatureGauge } from "./MarketTemperatureGauge";
import { MarketRegimeDashboard } from "./MarketRegimeDashboard";
import { OverviewFeatureRail } from "./OverviewFeatureRail";
import { OverviewMinuteChart } from "./OverviewMinuteChart";
import { OverviewTables } from "./OverviewTables";
import type { MarketOverviewLoader, MarketOverviewResponse, OverviewIndexQuote } from "./types";
import { TerminalPageHeader } from "../../shared/terminal/TerminalPrimitives";
import { BreakingNewsStrip } from "../news-alerts/BreakingNewsStrip";
import type { BreakingNewsAlertLoader } from "../news-alerts/types";
import { useBreakingNewsAlerts } from "../news-alerts/useBreakingNewsAlerts";
import { AnomalyVoiceAnnouncer } from "../speech/AnomalyVoiceAnnouncer";
import type { SpeechSynthesizer } from "../speech/types";
import { isAShareSymbol } from "../instrument-selection/SelectedInstrumentProvider";
import { DistinctMarketWorkspace } from "./workspaces/DistinctMarketWorkspace";
import { HomepageStartupOverlay } from "./HomepageStartupOverlay";
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

function keepAShareInformation(response: MarketOverviewResponse): MarketOverviewResponse {
  const liveFeed = response.live_feed
    .map((item) => ({ ...item, symbols: item.symbols.filter(isAShareSymbol) }))
    .filter((item) => item.symbols.length > 0);
  const anomalies = response.anomalies
    .map((item) => ({ ...item, symbols: item.symbols.filter(isAShareSymbol) }))
    .filter((item) => item.symbols.length > 0);
  return { ...response, live_feed: liveFeed, anomalies };
}

export function MarketOverviewView({ load, loadAlerts, onOpenAShare, synthesizeSpeech }: {
  load: MarketOverviewLoader;
  loadAlerts?: BreakingNewsAlertLoader;
  onOpenAShare?: (symbol: string) => void;
  synthesizeSpeech?: SpeechSynthesizer;
}) {
  const [data, setData] = useState<MarketOverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [visible, setVisible] = useState(document.visibilityState !== "hidden");
  const [activeFeature, setActiveFeature] = useState("盘中异动");
  const [selectedAnomalyId, setSelectedAnomalyId] = useState<string | null>(null);
  const [selectedSectorId, setSelectedSectorId] = useState<string | null>(null);
  const [searchSymbol, setSearchSymbol] = useState("");
  const requestRef = useRef<AbortController | null>(null);
  const alertState = useBreakingNewsAlerts(loadAlerts, undefined, 6);
  const aShareAlertState = useMemo(() => ({
    ...alertState,
    alerts: alertState.alerts.filter((alert) => alert.affected_symbols.some(isAShareSymbol)),
  }), [alertState]);

  const refresh = useCallback(async () => {
    if (requestRef.current !== null) return;
    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    try {
      const next = keepAShareInformation(await load(controller.signal));
      if (controller.signal.aborted) return;
      setData(next);
      setError(null);
      setSelectedAnomalyId((current) => current && next.anomalies.some((item) => item.anomaly_id === current) ? current : null);
      setSelectedSectorId((current) => current && next.sectors.some((item) => item.sector_id === current) ? current : next.sectors[0]?.sector_id ?? null);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "信息总览数据暂不可用");
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
        if (!controller.signal.aborted) setLoading(false);
      }
    }
  }, [load]);

  useEffect(() => {
    void refresh();
    return () => {
      requestRef.current?.abort();
      requestRef.current = null;
    };
  }, [refresh]);

  useEffect(() => {
    const onVisibility = () => setVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    if (!autoRefresh || !visible) return;
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, refresh, visible]);

  const focusedRegion = anomalyFeatures.has(activeFeature)
    ? "anomalies"
    : feedFeatures.has(activeFeature) ? "feed" : "sectors";
  const slots = useMemo(() => indexSlots(data?.indices ?? []), [data?.indices]);
  const selectedAnomaly = data?.anomalies.find((item) => item.anomaly_id === selectedAnomalyId) ?? null;

  const statusLabel = !data && loading
    ? "正在聚合 A 股市场数据"
    : error && !data ? "数据链路中断"
    : data?.status === "ready" ? "实时数据就绪"
    : data?.status === "partial" ? "部分数据可用"
    : "当前数据不可用";
  const marketData = data?.market_data;
  const coverage = marketData
    ? `${marketData.quote_count.toLocaleString("zh-CN")} / ${marketData.universe_count.toLocaleString("zh-CN")}`
    : "-- / --";

  const openSearchedSymbol = () => {
    const symbol = searchSymbol.trim();
    if (isAShareSymbol(symbol)) onOpenAShare?.(symbol);
  };

  return <main className="terminal-page market-overview-page">
    <HomepageStartupOverlay data={data} error={error} loading={loading} onRetry={() => void refresh()} />
    <TerminalPageHeader
      className="overview-terminal-header"
      eyebrow="A-SHARE / MARKET OVERVIEW"
      title="信息总览"
      description="A 股全市场行情、情绪、异动、题材与关联资讯同屏监测"
      actions={<div className={`overview-status ${data?.status ?? "unavailable"}`}>
        <Activity size={15} />
        <span><b>{statusLabel}</b><small>{data ? `${coverage} 行情覆盖` : "等待首次快照"}</small></span>
      </div>}
    />
    <div className="overview-sr-only" role="status">{statusLabel}</div>

    {error && <div className="overview-error"><AlertTriangle size={15} /><span>{error}</span>{data && <small>保留上一次成功快照</small>}</div>}

    <section className="overview-market-strip" aria-label="A 股市场情绪与核心指数">
      <MarketTemperatureGauge sentiment={data?.sentiment ?? { score: null, band: "等待数据", coverage_percent: "0", quality: "unavailable", observed_at: new Date().toISOString() }} />
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

    {loadAlerts && <BreakingNewsStrip {...aShareAlertState} onOpenAShare={onOpenAShare} />}

    <OverviewFeatureRail active={activeFeature} onSelect={setActiveFeature} />

    <div className="overview-toolbar">
      <button type="button" aria-label="立即刷新" disabled={loading} onClick={() => void refresh()}><RefreshCw size={14} className={loading ? "spinning" : ""} />刷新</button>
      <label><input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} />自动刷新</label>
      <span>间隔 <b>5</b> 秒</span>
      <span>当前筛选 <strong>{activeFeature}</strong></span>
      {!visible && <span className="overview-paused">页面隐藏，刷新已暂停</span>}
      {data && <time dateTime={data.observed_at}>更新于 {timeLabel(data.observed_at, true)}</time>}
    </div>

    {activeFeature === "盘中异动" && <><section className="overview-workspace">
      <section className={`overview-chart-panel ${focusedRegion === "anomalies" ? "focused" : ""}`} aria-label="上证指数分时与异动">
        <header><div><b>上证指数分时</b><span>价格 / 成交量 / 题材事件钉扎</span></div>{selectedAnomaly && <strong>{selectedAnomaly.label}</strong>}</header>
        <div className="overview-chart-shell"><OverviewMinuteChart points={data?.minute_series ?? []} anomalies={data?.anomalies ?? []} selectedAnomalyId={selectedAnomalyId} /></div>
      </section>

      <section className={`overview-anomaly-panel ${focusedRegion === "anomalies" ? "focused" : ""}`} aria-label="异动记录">
        <header><b>异动记录</b><span>{data?.anomalies.length ?? 0} 条</span></header>
        <div className="overview-anomaly-list">{(data?.anomalies.length ?? 0) === 0
          ? <p className="overview-empty">暂无已验证异动</p>
          : data?.anomalies.map((item) => <button
            key={item.anomaly_id} type="button" aria-pressed={selectedAnomalyId === item.anomaly_id}
            aria-label={`${timeLabel(item.occurred_at)} ${item.label}`}
            onClick={() => setSelectedAnomalyId(item.anomaly_id)}
          ><time>{timeLabel(item.occurred_at)}</time><span><b>{item.label}</b><small>{item.headline}</small></span></button>)}</div>
      </section>

      <section className={`overview-feed-panel ${focusedRegion === "feed" ? "focused" : ""}`} aria-label="A 股关联资讯">
        <header><div><b>A 股关联资讯</b><span>仅保留已关联 A 股的公开来源</span></div><Activity size={15} /></header>
        <div className="overview-feed-list">{(data?.live_feed.length ?? 0) === 0
          ? <p className="overview-empty">暂无已关联 A 股的实时资讯</p>
          : data?.live_feed.map((item) => <article key={item.event_id}>
            <time><Clock3 size={12} />{timeLabel(item.occurred_at)}</time><h2>{item.headline}</h2>
            {item.summary && <p>{item.summary}</p>}
            <div>{item.themes.map((theme) => <span key={theme}>{theme}</span>)}<small>{item.source}</small></div>
          </article>)}</div>
      </section>
    </section>

    <div className={focusedRegion === "sectors" ? "overview-tables-focused" : ""}>
      <OverviewTables sectors={data?.sectors ?? []} sectorStocks={data?.sector_stocks ?? {}} selectedSectorId={selectedSectorId} onSelectSector={setSelectedSectorId} onOpenAShare={onOpenAShare} />
    </div></>}

    {activeFeature === "情绪周期" && data?.regime_metrics && data.regime
      ? <MarketRegimeDashboard metrics={data.regime_metrics} regime={data.regime} />
      : activeFeature === "异动语音播报" && synthesizeSpeech
        ? <AnomalyVoiceAnnouncer anomalies={data?.anomalies ?? []} synthesize={synthesizeSpeech} />
        : activeFeature !== "盘中异动" && data && <DistinctMarketWorkspace feature={activeFeature} data={data} onOpenAShare={onOpenAShare} />}

    <footer className="overview-footnote">
      <span>来源：{data?.sources.join(" / ") || "等待数据"}</span>
      {data?.warnings.map((warning) => <span key={warning}><AlertTriangle size={12} />{warning}</span>)}
      <small>仅作信息观察，不构成投资建议</small>
    </footer>
  </main>;
}
