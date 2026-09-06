import { Activity, AlertTriangle, Maximize2, Minimize2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import type { MarketOverviewLoader, MarketOverviewResponse, MarketReviewStock } from "../market-overview/types";
import type { FirstLimitUpBoard } from "../first-limit-up/types";
import type { LateSessionSelectionResponse } from "../late-session-selection/types";
import type { BreakingNewsAlertLoader, BreakingNewsAlertResponse } from "../news-alerts/types";
import type { QuantStrategyDashboard } from "../quant-analysis/types";
import { useRealtimeSubscription, useRealtimeState } from "../../shared/realtime/RealtimeProvider";
import { TerminalPageHeader, TerminalPanel, TerminalStateNotice } from "../../shared/terminal/TerminalPrimitives";
import { buildDataScreenModel } from "./presenter";
import { findChangedSectorIds, sectorHighlightSignature } from "./sectorHighlights";
import type { DataScreenTone } from "./types";
import { DataScreenCharts } from "./DataScreenCharts";
import { dataScreenSessionLabel, dataScreenSessionState } from "./marketSessionState";
import { A_SHARE_WATCHLIST_CHANGED_EVENT, readAShareWatchlist } from "../stock-cockpit/watchlist";
import { loadOverseasMarket, type OverseasInstrumentQuote, type OverseasMarketSnapshot } from "./overseasMarket";
import "./dataScreen.css";
import "./dataScreenViewport.css";

function displayNumber(value: number | null, digits = 0): string {
  if (value === null || !Number.isFinite(value)) return "--";
  return value.toLocaleString("zh-CN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}
function signed(value: number | null, digits = 2): string { return value === null ? "--" : `${value >= 0 ? "+" : ""}${displayNumber(value, digits)}%`; }
function signedPoints(value: number | null): string { return value === null || !Number.isFinite(value) ? "--" : `${value >= 0 ? "+" : ""}${displayNumber(value, 2)}点`; }
function toneClass(tone: DataScreenTone): string { return tone === "up" ? "data-screen-up" : tone === "down" ? "data-screen-down" : tone === "flat" ? "data-screen-flat" : "data-screen-unavailable"; }
function freshnessLabel(value: string): string { return ({ live: "实时", previous_close: "昨收快照", final: "收盘", stale: "历史快照", unavailable: "不可用" } as Record<string, string>)[value] ?? "待确认"; }
function formatTime(value: string): string { const date = new Date(value); return Number.isNaN(date.getTime()) ? "--:--" : new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Shanghai" }).format(date); }
function marketSessionHint(phase: string, clock: Date): string {
  const parts = new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, timeZone: "Asia/Shanghai" }).formatToParts(clock);
  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? 0);
  const second = Number(parts.find((part) => part.type === "second")?.value ?? 0);
  const nowSeconds = hour * 3600 + minute * 60 + second;
  const target = phase === "premarket" ? 9 * 3600 + 30 * 60 : phase === "intraday" ? 15 * 3600 : null;
  if (target === null) return phase === "postclose" ? "下一交易日开盘 09:30" : "等待下一交易时段";
  const remaining = Math.max(0, target - nowSeconds);
  const hh = Math.floor(remaining / 3600).toString().padStart(2, "0");
  const mm = Math.floor((remaining % 3600) / 60).toString().padStart(2, "0");
  const ss = (remaining % 60).toString().padStart(2, "0");
  return phase === "premarket" ? `距开盘 ${hh}:${mm}:${ss}` : `距收盘 ${hh}:${mm}:${ss}`;
}

function overseasTone(quote: OverseasInstrumentQuote): string {
  const change = Number(quote.change_percent);
  return change > 0 ? "data-screen-up" : change < 0 ? "data-screen-down" : "data-screen-flat";
}

function formatOverseasNumber(value: string): string {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "--";
}

function newsVerificationLabel(value: BreakingNewsAlertResponse["alerts"][number]["verification_state"]): string {
  return value === "verified" || value === "multi_source_confirmed" ? "已核验" : value === "pending" ? "待核验" : "未核验";
}

function newsImpactLabel(value: BreakingNewsAlertResponse["alerts"][number]["impact_direction"]): string {
  return value === "positive" ? "正向" : value === "negative" ? "风险" : "中性";
}

function OverseasMarketPanel({ snapshot }: { snapshot: OverseasMarketSnapshot | null }) {
  const quality = snapshot?.quality ?? "unavailable";
  const label = snapshot?.trading_label ?? "美股行情暂不可用";
  const reason = snapshot?.reason;
  const renderQuote = (quote: OverseasInstrumentQuote) => <article key={quote.symbol} className={`data-screen-overseas-quote ${quote.quality !== "ready" ? "is-stale" : ""}`}>
    <header><b>{quote.name}</b><small>{quote.ticker}</small></header>
    <strong className={overseasTone(quote)}>{formatOverseasNumber(quote.price)}</strong>
    <span className={overseasTone(quote)}>{Number(quote.change) >= 0 ? "+" : ""}{formatOverseasNumber(quote.change)} · {Number(quote.change_percent) >= 0 ? "+" : ""}{formatOverseasNumber(quote.change_percent)}%</span>
    <small className="data-screen-overseas-state">{quote.trading_state} · {quote.quality === "stale" ? "数据陈旧" : "真实行情"}</small>
  </article>;
  return <section className={`data-screen-overseas-panel quality-${quality}`} aria-label="美股八个风向标">
    <header className="data-screen-overseas-header"><div><h2>隔夜外盘</h2><span>{label} · 来源：腾讯财经</span></div><b>{quality === "ready" ? "已接入" : quality === "stale" ? "数据陈旧" : "暂不可用"}</b></header>
    {quality === "unavailable" && <p className="data-screen-overseas-reason">{reason ?? "暂无有效美股行情，未展示伪造数据。"}</p>}
    <div className="data-screen-overseas-indices">{snapshot?.indices.map(renderQuote) ?? <span>等待真实指数行情</span>}</div>
    <div className="data-screen-overseas-mag7">{snapshot?.mag7.map(renderQuote) ?? <span>等待海外风向标行情</span>}</div>
    <p className="data-screen-overseas-note">美股港股的涨跌幅都是对比它们各自的前一交易日收盘。港股在北京时间白天可能正在交易，所以会标「盘中」——那是抓取那一刻的延时行情，没标具体几点。</p>
  </section>;
}

function marketChangeSignature(snapshot: MarketOverviewResponse): string {
  return JSON.stringify({
    observed_at: snapshot.observed_at,
    indices: snapshot.indices.map((item) => [item.instrument, item.value, item.change, item.change_percent]),
    breadth: snapshot.breadth,
    limits: snapshot.limit_ecology,
    liquidity: snapshot.liquidity,
    sectors: snapshot.sectors.map((item) => [item.sector_id, item.change_percent, item.amount_yi, item.rising_count, item.falling_count]),
    sector_fund_flow: (snapshot.sector_fund_flow ?? []).map((item) => [item.sector_code, item.observed_at, item.main_net_yi, item.large_net_yi, item.super_net_yi]),
    market_stocks: snapshot.market_stocks.slice(0, 80).map((item) => [item.symbol, item.price, item.change_percent, item.volume_ratio, item.turnover_rate]),
  });
}

const SECTOR_HIGHLIGHT_DURATION_MS = 10_000;

function useRotatingWindow<T>(items: T[], limit: number, identity: string, intervalMs = 4500, paused = false) {
  const [offset, setOffset] = useState(0);
  useEffect(() => { setOffset(0); }, [identity, limit]);
  useEffect(() => {
    if (items.length <= limit || paused) return;
    const timer = window.setInterval(() => setOffset((current) => (current + limit) % items.length), intervalMs);
    return () => window.clearInterval(timer);
  }, [items.length, limit, intervalMs, paused]);
  const visible = useMemo(() => {
    if (items.length <= limit) return items;
    return Array.from({ length: Math.min(limit, items.length) }, (_, index) => items[(offset + index) % items.length]);
  }, [items, limit, offset]);
  return { items: visible, offset, total: items.length };
}

function ContinuousRail<T>({ items, loopThreshold = 5, loopCopies = 2, cadenceSeconds = 4, className = "", itemKey, children }: {
  items: T[];
  loopThreshold?: number;
  loopCopies?: number;
  cadenceSeconds?: number;
  className?: string;
  itemKey: (item: T, index: number) => string;
  children: (item: T, index: number) => ReactNode;
}) {
  const looping = items.length > loopThreshold;
  const trackItems = looping ? Array.from({ length: Math.max(2, loopCopies) }, () => items).flat() : items;
  // Keep a constant readable cadence: account for the duplicated track that
  // crosses the viewport during the -50% loop, so more copies never make rows
  // pass by faster than the configured per-item reading time.
  const traversedCopies = looping ? Math.max(1, Math.floor(trackItems.length / Math.max(1, items.length) / 2)) : 1;
  const loopStyle = { "--data-screen-loop-duration": `${Math.max(1, items.length * cadenceSeconds * traversedCopies)}s` } as CSSProperties;
  return <div className={`data-screen-loop-viewport${looping ? " is-looping" : ""} ${className}`.trim()}>{trackItems.length > 0 ? <div className="data-screen-loop-track" style={loopStyle}>{trackItems.map((item, index) => <div key={`${itemKey(item, index % Math.max(1, items.length))}-${index}`} className="data-screen-loop-item">{children(item, index % Math.max(1, items.length))}</div>)}</div> : <span className="data-screen-inline-empty">暂无数据</span>}</div>;
}

function LimitLadderRail({ title, items, onOpenAShare }: { title: string; items: MarketReviewStock[]; onOpenAShare?: (symbol: string) => void }) {
  return <section className="data-screen-ladder-column" role="region" aria-label={title}>
    <h3>{title}<small>{items.length ? `${items.length} 只` : "暂无数据"}</small></h3>
    <ContinuousRail items={items} loopThreshold={5} loopCopies={2} className="data-screen-ladder-rail" itemKey={(item) => item.symbol}>
      {(item) => <button type="button" className="data-screen-ladder-row" onClick={() => onOpenAShare?.(item.symbol)}>
        <span><b>{item.name || "名称待补"}</b><small>{item.symbol}</small></span>
        <strong className="data-screen-up">{item.board_count === null ? "首板" : `${item.board_count}板`}</strong>
        <em>{item.change_percent ? `${Number(item.change_percent) >= 0 ? "+" : ""}${item.change_percent}%` : "--"}</em>
      </button>}
    </ContinuousRail>
  </section>;
}

function LimitEcologyStats({ sealed, sealRate, broken, brokenRate, promoted, promotionRate }: {
  sealed: number | null;
  sealRate: number | null;
  broken: number | null;
  brokenRate: number | null;
  promoted: number | null;
  promotionRate: number | null;
}) {
  const rate = (value: number | null) => value === null || !Number.isFinite(value) ? "--" : `${value.toFixed(1)}%`;
  return <section className="data-screen-limit-ecology-section" aria-label="封板生态统计">
    <h3>封板生态 <small>实时统计</small></h3>
    <div className="data-screen-limit-ecology-grid">
      <div className="data-screen-limit-ecology-card data-screen-up"><small>封板数量</small><strong>{displayNumber(sealed)}</strong><span>封板率 {rate(sealRate)}</span><small>封住 / 尝试涨停</small></div>
      <div className="data-screen-limit-ecology-card data-screen-down"><small>炸板数量</small><strong>{displayNumber(broken)}</strong><span>炸板率 {rate(brokenRate)}</span><small>炸板 / 尝试涨停</small></div>
      <div className="data-screen-limit-ecology-card data-screen-gold"><small>晋级数量</small><strong>{displayNumber(promoted)}</strong><span>晋级率 {rate(promotionRate)}</span><small>前一交易日涨停的票，又封住</small></div>
    </div>
  </section>;
}

function CapitalRotationBoard({ inflow, outflow }: { inflow: Array<{ code: string; name: string; net: number | null; changePercent: number | null }>; outflow: Array<{ code: string; name: string; net: number | null; changePercent: number | null }> }) {
  const renderColumn = (title: string, rows: Array<{ code: string; name: string; net: number | null; changePercent: number | null }>, tone: "up" | "down") => {
    const slots = Array.from({ length: 6 }, (_, index) => rows[index] ?? null);
    return <section className={`data-screen-capital-rotation-column data-screen-${tone}`} aria-label={title}>
      <h3>{title}<small>{rows.length ? `${rows.length} 个行业` : "暂无数据"}</small></h3>
      <div className="data-screen-capital-rotation-list" role="list">
        {slots.map((row, index) => <div key={row?.code ?? `${tone}-placeholder-${index}`} className={`data-screen-capital-rotation-row${row ? "" : " is-placeholder"}`} role="listitem">
          <i>{index + 1}</i><b>{row?.name ?? (rows.length ? "暂无更多行业" : tone === "down" ? "暂无净流出行业" : "暂无净流入行业")}</b><span>{row?.changePercent === null || row?.changePercent === undefined || !Number.isFinite(row.changePercent) ? "--" : `${row.changePercent >= 0 ? "+" : ""}${row.changePercent.toFixed(2)}%`}</span><strong>{row?.net === null || row?.net === undefined || !Number.isFinite(row.net) ? "--" : `${row.net >= 0 ? "+" : ""}${row.net.toFixed(2)} 亿`}</strong>
        </div>)}
      </div>
    </section>;
  };
  return <section className="data-screen-capital-rotation" aria-label="资金轮动"><header><span>资金轮动</span><small>行业主力净流入 / 流出</small></header><div className="data-screen-capital-rotation-pair">{renderColumn("流入 Top", inflow, "up")}{renderColumn("流出 Top", outflow, "down")}</div></section>;
}

function Sparkline({ values, tone = "up" }: { values: Array<number | null>; tone?: DataScreenTone }) {
  const clean = values.filter((value): value is number => value !== null && Number.isFinite(value));
  if (clean.length < 2) return <div className="data-screen-chart-empty">分时数据等待中</div>;
  const min = Math.min(...clean); const max = Math.max(...clean); const span = max - min || 1;
  const points = clean.map((value, index) => `${(index / (clean.length - 1)) * 100},${96 - ((value - min) / span) * 78}`).join(" ");
  return <svg className={`data-screen-sparkline ${toneClass(tone)}`} viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="实时分时走势"><polyline points={points} fill="none" vectorEffect="non-scaling-stroke" /></svg>;
}

type DataScreenViewProps = {
  load: MarketOverviewLoader;
  loadLateSession?: () => Promise<LateSessionSelectionResponse>;
  loadFirstLimitUp?: () => Promise<FirstLimitUpBoard>;
  loadAlerts?: BreakingNewsAlertLoader;
  loadQuantStrategy?: (limit?: number) => Promise<QuantStrategyDashboard>;
  onOpenAShare?: (symbol: string) => void;
};

export function DataScreenView({ load, loadLateSession, loadFirstLimitUp, loadAlerts, loadQuantStrategy, onOpenAShare }: DataScreenViewProps) {
  const [snapshot, setSnapshot] = useState<MarketOverviewResponse | null>(null);
  const [lateSession, setLateSession] = useState<LateSessionSelectionResponse | null>(null);
  const [firstLimitUp, setFirstLimitUp] = useState<FirstLimitUpBoard | null>(null);
  const [alerts, setAlerts] = useState<BreakingNewsAlertResponse | null>(null);
  const [quantStrategy, setQuantStrategy] = useState<QuantStrategyDashboard | null>(null);
  const [overseasMarket, setOverseasMarket] = useState<OverseasMarketSnapshot | null>(null);
  const [overseasError, setOverseasError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [clock, setClock] = useState(() => new Date());
  const requestRef = useRef<AbortController | null>(null);
  const auxRequestRef = useRef<AbortController | null>(null);
  const pulseTimerRef = useRef<number | null>(null);
  const auxiliarySignatureRef = useRef<string | null>(null);
  const quantIdsRef = useRef<Set<string> | null>(null);
  const quantLeavingTimersRef = useRef<Map<string, number>>(new Map());
  const quantHotTimersRef = useRef<Map<string, number>>(new Map());
  const sectorSignaturesRef = useRef<Map<string, string> | null>(null);
  const sectorHotTimersRef = useRef<Map<string, number>>(new Map());
  const quantStrategyRef = useRef<QuantStrategyDashboard | null>(null);
  const [quantHotSymbols, setQuantHotSymbols] = useState<Set<string>>(() => new Set());
  const [sectorHotIds, setSectorHotIds] = useState<Set<string>>(() => new Set());
  const [quantLeaving, setQuantLeaving] = useState<QuantStrategyDashboard["candidates"]>([]);
  const [pulseActive, setPulseActive] = useState(false);
  const [watchlistSymbols, setWatchlistSymbols] = useState<string[]>(readAShareWatchlist);
  const dataRef = useRef<MarketOverviewResponse | null>(null);
  dataRef.current = snapshot;
  const realtimeState = useRealtimeState();
  const triggerPulse = useCallback(() => {
    setPulseActive(true);
    if (pulseTimerRef.current !== null) window.clearTimeout(pulseTimerRef.current);
    pulseTimerRef.current = window.setTimeout(() => setPulseActive(false), 1100);
  }, []);
  const applySectorHighlights = useCallback((incoming: MarketOverviewResponse) => {
    const displayedSectors = buildDataScreenModel(incoming).sectors;
    const nextSignatures = new Map(displayedSectors.map((sector) => [sector.sector_id, sectorHighlightSignature(sector)]));
    const changedIds = findChangedSectorIds(sectorSignaturesRef.current, displayedSectors);
    sectorSignaturesRef.current = nextSignatures;
    if (changedIds.length === 0) return;
    setSectorHotIds((current) => new Set([...current, ...changedIds]));
    changedIds.forEach((sectorId) => {
      const existing = sectorHotTimersRef.current.get(sectorId);
      if (existing !== undefined) window.clearTimeout(existing);
      const timer = window.setTimeout(() => {
        sectorHotTimersRef.current.delete(sectorId);
        setSectorHotIds((current) => {
          const next = new Set(current);
          next.delete(sectorId);
          return next;
        });
      }, SECTOR_HIGHLIGHT_DURATION_MS);
      sectorHotTimersRef.current.set(sectorId, timer);
    });
    triggerPulse();
  }, [triggerPulse]);
  const applyAlerts = useCallback((incoming: BreakingNewsAlertResponse) => {
    setAlerts(incoming);
  }, []);
  const applyQuantStrategy = useCallback((incoming: QuantStrategyDashboard) => {
    const incomingIds = new Set(incoming.candidates.map((candidate) => candidate.symbol));
    const previousIds = quantIdsRef.current;
    const added = incoming.candidates.filter((candidate) => previousIds === null || !previousIds.has(candidate.symbol)).map((candidate) => candidate.symbol);
    const removed = previousIds ? [...previousIds].filter((symbol) => !incomingIds.has(symbol)) : [];
    if (removed.length > 0) {
      const removedCandidates = (quantStrategyRef.current?.candidates ?? []).filter((candidate) => removed.includes(candidate.symbol));
      setQuantLeaving(removedCandidates);
      removedCandidates.forEach((candidate) => {
        const existing = quantLeavingTimersRef.current.get(candidate.symbol);
        if (existing !== undefined) window.clearTimeout(existing);
        const timer = window.setTimeout(() => {
          setQuantLeaving((current) => current.filter((item) => item.symbol !== candidate.symbol));
          quantLeavingTimersRef.current.delete(candidate.symbol);
        }, 900);
        quantLeavingTimersRef.current.set(candidate.symbol, timer);
      });
    }
    quantIdsRef.current = incomingIds;
    quantStrategyRef.current = incoming;
    setQuantStrategy(incoming);
    if (added.length > 0) {
      setQuantHotSymbols((current) => new Set([...current, ...added]));
      added.forEach((symbol) => {
        const existing = quantHotTimersRef.current.get(symbol);
        if (existing !== undefined) window.clearTimeout(existing);
        const timer = window.setTimeout(() => {
          quantHotTimersRef.current.delete(symbol);
          setQuantHotSymbols((current) => { const next = new Set(current); next.delete(symbol); return next; });
        }, 12000);
        quantHotTimersRef.current.set(symbol, timer);
      });
      triggerPulse();
    }
  }, [triggerPulse]);
  const apply = useCallback((incoming: MarketOverviewResponse) => {
    const currentSnapshot = dataRef.current;
    const currentAt = currentSnapshot ? Date.parse(currentSnapshot.observed_at) : Number.NaN;
    const incomingAt = Date.parse(incoming.observed_at);
    if (currentSnapshot && Number.isFinite(incomingAt) && Number.isFinite(currentAt) && incomingAt < currentAt) return;
    applySectorHighlights(incoming);
    setSnapshot((current) => {
      if (!current) return incoming;
      const currentAt = Date.parse(current.observed_at); const incomingAt = Date.parse(incoming.observed_at);
      if (marketChangeSignature(current) !== marketChangeSignature(incoming)) {
        triggerPulse();
      }
      return Number.isFinite(incomingAt) && Number.isFinite(currentAt) && incomingAt < currentAt ? current : incoming;
    });
    setError(null);
  }, [applySectorHighlights, triggerPulse]);
  const refresh = useCallback(async () => {
    if (requestRef.current) return;
    const controller = new AbortController(); requestRef.current = controller; setLoading(!dataRef.current);
    try { apply(await load(controller.signal)); }
    catch (reason) { if (!(reason instanceof DOMException && reason.name === "AbortError")) setError(reason instanceof Error ? reason.message : "数据加载失败"); }
    finally { if (requestRef.current === controller) { requestRef.current = null; setLoading(false); } }
  }, [apply, load]);
  const refreshAuxiliary = useCallback(async () => {
    if (auxRequestRef.current) return;
    const controller = new AbortController();
    auxRequestRef.current = controller;
    const jobs = await Promise.all([
      loadLateSession ? loadLateSession().catch(() => null) : Promise.resolve(null),
      loadFirstLimitUp ? loadFirstLimitUp().catch(() => null) : Promise.resolve(null),
      loadAlerts ? loadAlerts(null, controller.signal, 12).catch(() => null) : Promise.resolve(null),
      loadQuantStrategy ? loadQuantStrategy(24).catch(() => null) : Promise.resolve(null),
    ]);
    const [nextLateSession, nextFirstLimitUp, nextAlerts, nextQuantStrategy] = jobs;
    const signature = [
      nextLateSession?.server_time ?? "", nextLateSession?.candidate_count ?? "", nextLateSession?.candidates?.map((item) => `${item.quote.symbol}:${item.last_updated_at}`).join(",") ?? "",
      nextFirstLimitUp?.scan_updated_at ?? "", nextFirstLimitUp?.qualified_count ?? "",
      nextAlerts?.observed_at ?? "", nextAlerts?.alerts?.map((item) => `${item.event_id}:${item.headline}:${item.occurred_at}:${item.urgency}:${item.impact_direction}`).join(",") ?? "",
      nextQuantStrategy?.observed_at ?? "", nextQuantStrategy?.candidates?.map((item) => `${item.symbol}:${item.factor_as_of}:${item.status}`).join(",") ?? "",
    ].join("|");
    if (auxiliarySignatureRef.current && auxiliarySignatureRef.current !== signature) triggerPulse();
    auxiliarySignatureRef.current = signature;
    if (nextLateSession) setLateSession(nextLateSession);
    if (nextFirstLimitUp) setFirstLimitUp(nextFirstLimitUp);
    if (nextAlerts) applyAlerts(nextAlerts);
    if (nextQuantStrategy) applyQuantStrategy(nextQuantStrategy);
    if (auxRequestRef.current === controller) auxRequestRef.current = null;
  }, [applyAlerts, applyQuantStrategy, loadAlerts, loadFirstLimitUp, loadLateSession, loadQuantStrategy, triggerPulse]);
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 5000); return () => { window.clearInterval(timer); requestRef.current?.abort(); }; }, [refresh]);
  useEffect(() => {
    void refreshAuxiliary();
    const timer = window.setInterval(() => void refreshAuxiliary(), 5000);
    return () => {
      window.clearInterval(timer);
      auxRequestRef.current?.abort();
      if (pulseTimerRef.current !== null) window.clearTimeout(pulseTimerRef.current);
      quantLeavingTimersRef.current.forEach((timerId) => window.clearTimeout(timerId));
      quantLeavingTimersRef.current.clear();
      quantHotTimersRef.current.forEach((timerId) => window.clearTimeout(timerId));
      quantHotTimersRef.current.clear();
      sectorHotTimersRef.current.forEach((timerId) => window.clearTimeout(timerId));
      sectorHotTimersRef.current.clear();
    };
  }, [refreshAuxiliary]);
  useEffect(() => {
    const controller = new AbortController();
    const refreshOverseas = async () => {
      try {
        const next = await loadOverseasMarket(controller.signal);
        setOverseasMarket(next);
        setOverseasError(null);
      } catch (reason) {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) setOverseasError(reason instanceof Error ? reason.message : "美股风向标加载失败");
      }
    };
    void refreshOverseas();
    const timer = window.setInterval(() => void refreshOverseas(), 5000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, []);
  useRealtimeSubscription("late_session_candidates", () => { void refreshAuxiliary(); });
  useRealtimeSubscription("news_events", () => { void refreshAuxiliary(); });
  useRealtimeSubscription<{
    snapshot_id?: string;
    observed_at?: string;
    source?: string;
    items?: Array<{
      sector_code: string;
      sector_name: string;
      main_net_yi: string | number;
      large_net_yi?: string | number | null;
      super_net_yi?: string | number | null;
    }>;
  }>("sector_fund_flow", (event) => {
    const payload = event.payload;
    if (!payload?.items?.length) return;
    const observedAt = payload.observed_at || event.observed_at;
    setSnapshot((current) => {
      if (!current) return current;
      const previous = current.sector_fund_flow ?? [];
      const incoming = payload.items!.map((item) => ({
        sector_code: item.sector_code,
        sector_name: item.sector_name,
        observed_at: observedAt,
        main_net_yi: String(item.main_net_yi),
        large_net_yi: item.large_net_yi == null ? null : String(item.large_net_yi),
        super_net_yi: item.super_net_yi == null ? null : String(item.super_net_yi),
        source: payload.source || event.source,
        quality: "ready" as const,
      }));
      const cutoff = Date.parse(observedAt);
      const retained = previous.filter((item) => {
        const itemTime = Date.parse(item.observed_at);
        return !Number.isFinite(cutoff) || !Number.isFinite(itemTime) || itemTime < cutoff;
      });
      return { ...current, sector_fund_flow: [...retained, ...incoming], observed_at: event.observed_at };
    });
    triggerPulse();
  });
  useRealtimeSubscription<MarketOverviewResponse>("market_overview", (event) => apply(event.payload));
  useEffect(() => { const onFullscreen = () => setFullscreen(Boolean(document.fullscreenElement)); document.addEventListener("fullscreenchange", onFullscreen); return () => document.removeEventListener("fullscreenchange", onFullscreen); }, []);
  useEffect(() => { const timer = window.setInterval(() => setClock(new Date()), 1000); return () => window.clearInterval(timer); }, []);
  useEffect(() => {
    const syncWatchlist = () => setWatchlistSymbols(readAShareWatchlist());
    window.addEventListener(A_SHARE_WATCHLIST_CHANGED_EVENT, syncWatchlist);
    return () => window.removeEventListener(A_SHARE_WATCHLIST_CHANGED_EVENT, syncWatchlist);
  }, []);
  const toggleFullscreen = useCallback(async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.querySelector(".data-screen-page")?.requestFullscreen();
  }, []);
  const model = useMemo(() => buildDataScreenModel(snapshot), [snapshot]);
  const sessionState = dataScreenSessionState(model.marketPhase, clock);
  const sessionLabel = dataScreenSessionLabel(sessionState);
  const waitingForOpen = sessionState === "waiting_open";
  const status = loading && !snapshot ? "loading" : error && !snapshot ? "error" : model.status === "unavailable" ? "unavailable" : error ? "stale" : model.status;
  const statusTitle = status === "loading" ? "正在聚合市场数据" : status === "error" ? "市场数据加载失败" : status === "stale" ? "实时更新暂时中断，继续显示最近快照" : status === "unavailable" ? "暂无有效市场数据" : waitingForOpen ? "等待开盘中" : "实时市场监控中";
  const statusDetail = error ?? `${sessionLabel} · ${model.coverage.label} · ${freshnessLabel(model.freshness)} · 实时通道 ${realtimeState === "connected" ? "在线" : "待命"}`;
  const breadthTotal = model.breadth.total ?? 0;
  const downPercent = breadthTotal ? (model.breadth.falling ?? 0) / breadthTotal * 100 : 0;
  const flatPercent = breadthTotal ? (model.breadth.flat ?? 0) / breadthTotal * 100 : 0;
  const indexByName = (name: string) => model.indices.find((index) => index.name === name);
  const shIndex = indexByName("上证指数");
  const szIndex = indexByName("深证成指");
  const cyIndex = indexByName("创业板指");
  const kcIndex = indexByName("科创50");
  const zzIndex = indexByName("中证500");
  const radarPool = useMemo(() => model.anomalies.length > 0
    ? model.anomalies.map((event) => ({ id: event.anomaly_id, direction: event.direction, headline: event.headline || event.label, symbols: event.symbols, occurred_at: event.occurred_at, strength: event.strength === "high" ? "高" : event.strength === "medium" ? "中" : "观察" }))
    : model.liveFeed.map((event) => ({ id: event.event_id, direction: "neutral" as const, headline: event.headline, symbols: event.symbols, occurred_at: event.occurred_at, strength: "资讯" })), [model.anomalies, model.liveFeed]);
  const radarWindow = useRotatingWindow(radarPool, 4, radarPool.map((event) => `${event.id}:${event.occurred_at}`).join(","), 4500);
  const newsAlerts = alerts?.alerts ?? [];
  const livePanelClass = pulseActive ? " data-screen-pulse" : "";
  const quantCandidates = [...(quantStrategy?.candidates ?? []), ...quantLeaving.filter((item) => !(quantStrategy?.candidates ?? []).some((candidate) => candidate.symbol === item.symbol))];
  const marketStocks = snapshot?.market_stocks ?? [];
  const watchlistStocks = watchlistSymbols.map((symbol) => marketStocks.find((item) => item.symbol === symbol)).filter(Boolean);
  const marketFocusStocks = [...marketStocks]
    .sort((left, right) => Math.abs(Number(right.change_percent ?? 0)) - Math.abs(Number(left.change_percent ?? 0)))
    .slice(0, 8);
  const displayedWatchlistStocks = watchlistStocks.length ? watchlistStocks : marketFocusStocks;
  const anomalyStocks = marketStocks.filter((stock) => Number(stock.volume_ratio ?? 0) > 2 || Math.abs(Number(stock.change_percent ?? 0)) >= 7 || Number(stock.turnover_rate ?? 0) >= 8);
  const quantOnlyStocks = quantCandidates
    .filter((candidate) => !marketStocks.some((stock) => stock.symbol === candidate.symbol))
    .map((candidate) => ({ symbol: candidate.symbol, name: candidate.name, price: "--", volume_ratio: null, turnover_rate: null, change_percent: null, quant_score: candidate.strategy_score }));
  const autoScanStocks = [...anomalyStocks, ...marketStocks.filter((stock) => quantCandidates.some((candidate) => candidate.symbol === stock.symbol)), ...quantOnlyStocks];
  const topicSectors = model.sectors.slice(0, 12);
  const realtimeNews = newsAlerts.slice(0, 10);
  const sectorFlowItems = model.sectorFlows;
  const sectorFlowWithChange = model.sectorFlows.map((flow) => ({
    ...flow,
    changePercent: flow.changePercent ?? (() => {
      const sector = model.sectors.find((item) => item.sector_id === flow.code || item.name === flow.name);
      return sector?.change_percent == null ? null : Number(sector.change_percent);
    })(),
  }));
  const capitalInflow = sectorFlowWithChange.filter((flow) => flow.net !== null && flow.net >= 0).sort((left, right) => (right.net ?? -Infinity) - (left.net ?? -Infinity)).slice(0, 6);
  const capitalOutflow = sectorFlowWithChange.filter((flow) => flow.net !== null && flow.net < 0).sort((left, right) => (left.net ?? Infinity) - (right.net ?? Infinity)).slice(0, 6);
  const limitUpStocks = marketStocks.filter((stock) => stock.state === "limit_up");
  const limitDownStocks = marketStocks.filter((stock) => stock.state === "limit_down");
  const consecutiveLadder = snapshot?.review?.consecutive_limit_up ?? [];
  const firstBoardLadder = snapshot?.review?.first_limit_up ?? firstLimitUp?.today.map((item) => ({
    symbol: item.symbol,
    name: item.name,
    trade_date: item.limit_up_date,
    category: "first_limit_up" as const,
    close: item.current_close,
    change_percent: item.limit_rate,
    amount_yi: "",
    source: item.sources.join(", "),
    board_count: 1,
    limit_statistics: "1/1",
    prior_close: null,
    prior_change_percent: null,
    turnover_rate: null,
    seal_amount_yi: null,
    failed_limit_count: null,
    first_seal_time: null,
    volume_multiple: null,
    reference_high: null,
    window_days: null,
    range_position_percent: null,
  })) ?? [];
  const sealedCount = model.limits.up;
  const brokenCount = model.limits.broken;
  const touchedCount = sealedCount !== null && brokenCount !== null ? sealedCount + brokenCount : null;
  const brokenRate = touchedCount !== null && touchedCount > 0 && brokenCount !== null ? brokenCount / touchedCount * 100 : null;
  const promotedCount = snapshot?.review ? snapshot.review.consecutive_limit_up.length : null;
  const promotionBase = snapshot?.review ? snapshot.review.previous_limit_up.length : null;
  const promotionRate = promotionBase !== null && promotionBase > 0 && promotedCount !== null ? promotedCount / promotionBase * 100 : null;
  return <main className="terminal-page data-screen-page data-screen-c3" data-fullscreen={fullscreen}>
    <div className="data-screen-hologram-corners" aria-hidden="true"><span className="corner-top-left" /><span className="corner-top-right" /><span className="corner-bottom-left" /><span className="corner-bottom-right" /></div>
    <TerminalPageHeader eyebrow="A-SHARE / DIGITAL TWIN" title="数据大屏" description="全市场实时态势 · 数字孪生流场 · 投影监控模式" actions={<div className="data-screen-header-actions"><div className="data-screen-live-status"><span className="data-screen-live-dot" /><b>{statusTitle}</b><small>{statusDetail} · 系统时间 {new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(clock)}</small></div><button className="data-screen-fullscreen-button" type="button" onClick={() => void toggleFullscreen()} aria-label={fullscreen ? "退出全屏" : "进入全屏"} title={fullscreen ? "退出全屏" : "进入全屏"}>{fullscreen ? <Minimize2 size={17} /> : <Maximize2 size={17} />}</button></div>} />
    {status !== "ready" && <TerminalStateNotice state={status === "partial" ? "partial" : status} title={statusTitle} detail={statusDetail} icon={status === "error" ? <AlertTriangle size={17} /> : <Activity size={17} />} className="data-screen-state" />}
    {overseasError && !overseasMarket && <TerminalStateNotice state="error" title="美股风向标加载失败" detail={overseasError} className="data-screen-state" />}
    <section className={`data-screen-kpi-ribbon${pulseActive ? " data-screen-pulse" : ""}`} aria-label="市场核心指标">
      <div><small>上证指数</small><strong className={waitingForOpen ? "data-screen-flat" : shIndex ? toneClass(shIndex.tone) : ""}>{waitingForOpen ? "等待开盘" : shIndex?.value ?? "--"}</strong><span className={waitingForOpen ? "data-screen-flat" : shIndex ? toneClass(shIndex.tone) : ""}>{waitingForOpen ? "正在等待开盘中" : shIndex ? `${signed(Number(shIndex.change_percent))} · ${signedPoints(Number(shIndex.change))}` : "暂未接入"}</span></div>
      <div><small>深证成指</small><strong className={waitingForOpen ? "data-screen-flat" : szIndex ? toneClass(szIndex.tone) : ""}>{waitingForOpen ? "等待开盘" : szIndex?.value ?? "--"}</strong><span className={waitingForOpen ? "data-screen-flat" : szIndex ? toneClass(szIndex.tone) : ""}>{waitingForOpen ? "正在等待开盘中" : szIndex ? `${signed(Number(szIndex.change_percent))} · ${signedPoints(Number(szIndex.change))}` : "暂未接入"}</span></div>
      <div><small>创业板指</small><strong className={waitingForOpen ? "data-screen-flat" : cyIndex ? toneClass(cyIndex.tone) : ""}>{waitingForOpen ? "等待开盘" : cyIndex?.value ?? "--"}</strong><span className={waitingForOpen ? "data-screen-flat" : cyIndex ? toneClass(cyIndex.tone) : ""}>{waitingForOpen ? "正在等待开盘中" : cyIndex ? `${signed(Number(cyIndex.change_percent))} · ${signedPoints(Number(cyIndex.change))}` : "暂未接入"}</span></div>
      <div><small>科创50</small><strong className={waitingForOpen ? "data-screen-flat" : kcIndex ? toneClass(kcIndex.tone) : ""}>{waitingForOpen ? "等待开盘" : kcIndex?.value ?? "--"}</strong><span className={waitingForOpen ? "data-screen-flat" : kcIndex ? toneClass(kcIndex.tone) : ""}>{waitingForOpen ? "正在等待开盘中" : kcIndex ? `${signed(Number(kcIndex.change_percent))} · ${signedPoints(Number(kcIndex.change))}` : "暂未接入"}</span></div>
      <div><small>中证500</small><strong className={waitingForOpen ? "data-screen-flat" : zzIndex ? toneClass(zzIndex.tone) : ""}>{waitingForOpen ? "等待开盘" : zzIndex?.value ?? "--"}</strong><span className={waitingForOpen ? "data-screen-flat" : zzIndex ? toneClass(zzIndex.tone) : ""}>{waitingForOpen ? "正在等待开盘中" : zzIndex ? `${signed(Number(zzIndex.change_percent))} · ${signedPoints(Number(zzIndex.change))}` : "暂未接入"}</span></div>
      <div><small>两市成交额</small><strong className="data-screen-kpi-gold">{waitingForOpen ? "等待开盘" : displayNumber(model.liquidity.total, 0)}</strong><span>{waitingForOpen ? "正在等待开盘中" : `亿元 · ${displayNumber(model.liquidity.relative, 2)}x基准`}</span></div>
      <div><small>上涨 / 下跌</small><strong className="data-screen-kpi-split">{waitingForOpen ? <span className="data-screen-flat">等待开盘</span> : <><span className="data-screen-up">{displayNumber(model.breadth.rising)}</span><i>/</i><span className="data-screen-down">{displayNumber(model.breadth.falling)}</span></>}</strong><span>{waitingForOpen ? "正在等待开盘中" : `平盘 ${displayNumber(model.breadth.flat)}`}</span></div>
      <div><small>涨停 / 跌停</small><strong className="data-screen-kpi-split">{waitingForOpen ? <span className="data-screen-flat">等待开盘</span> : <><span className="data-screen-up">{displayNumber(model.limits.up)}</span><i>/</i><span className="data-screen-down">{displayNumber(model.limits.down)}</span></>}</strong><span>{waitingForOpen ? "正在等待开盘中" : `封板率 ${model.limits.sealRate === null ? "--" : `${model.limits.sealRate.toFixed(1)}%`}`}</span></div>
      <div><small>平盘家数</small><strong className="data-screen-flat">{waitingForOpen ? "等待开盘" : displayNumber(model.breadth.flat)}</strong><span>{waitingForOpen ? "正在等待开盘中" : "市场中性"}</span></div>
      <div><small>市场情绪</small><strong className="data-screen-quantum">{waitingForOpen ? "等待开盘" : model.sentiment.score === null ? "--" : displayNumber(model.sentiment.score, 0)}</strong><span>{waitingForOpen ? "正在等待开盘中" : `${model.sentiment.band} · 覆盖 ${model.sentiment.coverage === null ? "--" : `${displayNumber(model.sentiment.coverage, 1)}%`}`}</span></div>
      <div><small>市场阶段</small><strong>{waitingForOpen ? "等待开盘" : model.marketPhase === "intraday" ? "盘中" : model.marketPhase === "premarket" ? "最近收盘" : model.marketPhase === "postclose" ? "收盘" : model.marketPhase === "closed" ? "最近收盘" : "待确认"}</strong><span>{waitingForOpen ? "正在等待开盘中" : marketSessionHint(model.marketPhase, clock)} · {model.coverage.label}</span></div>
    </section>
    <div className="data-screen-grid" aria-busy={loading}>
      <TerminalPanel title="" ariaLabel="行业板块列表" className={`data-screen-panel data-screen-panel-headerless data-screen-sectors${livePanelClass}`}>
        <div className="data-screen-sector-dashboard">
          <div className="data-screen-overseas-slot"><OverseasMarketPanel snapshot={overseasMarket} /></div>
          <LimitEcologyStats sealed={sealedCount} sealRate={model.limits.sealRate} broken={brokenCount} brokenRate={brokenRate} promoted={promotedCount} promotionRate={promotionRate} />
          <section className="data-screen-ladder-section" aria-label="涨停梯队"><div className="data-screen-ladder-pair"><LimitLadderRail title="连板梯队" items={consecutiveLadder} onOpenAShare={onOpenAShare} /><LimitLadderRail title="首板梯队" items={firstBoardLadder} onOpenAShare={onOpenAShare} /></div></section>
          <section className="data-screen-sector-alerts"><h3>异动板块</h3><div>{model.sectors.filter((sector) => Math.abs(Number(sector.change_percent ?? 0)) >= 2).slice(0, 4).map((sector) => <span key={sector.sector_id} className={toneClass(sector.tone)}><b>{sector.name}</b><em>{signed(Number(sector.change_percent))}</em></span>)}{model.sectors.filter((sector) => Math.abs(Number(sector.change_percent ?? 0)) >= 2).length === 0 && <span className="data-screen-empty">暂无快速拉升或跳水板块</span>}</div></section>
        </div>
      </TerminalPanel>
      <TerminalPanel title="指数与市场图表" subtitle={`${model.asOf || "--"} · ${freshnessLabel(model.freshness)}`} ariaLabel="指数与市场图表" className="data-screen-panel data-screen-indices">
        <div className="data-screen-center-monitor-stack">
          <DataScreenCharts model={model} newsAlerts={newsAlerts} showNews={false} />
          <section className="data-screen-center-limit-board" aria-label="当前涨跌停监控">
            <section className="data-screen-limit-flow-column data-screen-limit-up" role="region" aria-label="当前涨停股票"><h3>当前涨停 <small>{limitUpStocks.length} 只 · 循环滚动</small></h3><ContinuousRail items={limitUpStocks} loopThreshold={0} loopCopies={8} cadenceSeconds={1} className="data-screen-limit-flow-rail" itemKey={(stock) => stock.symbol}>{(stock) => <button type="button" className="data-screen-limit-stock-row" onClick={() => onOpenAShare?.(stock.symbol)}><b>{stock.name || "名称待补"}</b><small>{stock.symbol}</small><strong>{stock.price || "--"}</strong><span>{signed(Number(stock.change_percent))} · 量比 {stock.volume_ratio || "--"}</span></button>}</ContinuousRail></section>
            <section className="data-screen-limit-flow-column data-screen-limit-down" role="region" aria-label="当前跌停股票"><h3>当前跌停 <small>{limitDownStocks.length} 只 · 循环滚动</small></h3><ContinuousRail items={limitDownStocks} loopThreshold={0} loopCopies={8} cadenceSeconds={1} className="data-screen-limit-flow-rail" itemKey={(stock) => stock.symbol}>{(stock) => <button type="button" className="data-screen-limit-stock-row" onClick={() => onOpenAShare?.(stock.symbol)}><b>{stock.name || "名称待补"}</b><small>{stock.symbol}</small><strong>{stock.price || "--"}</strong><span>{signed(Number(stock.change_percent))} · 量比 {stock.volume_ratio || "--"}</span></button>}</ContinuousRail></section>
          </section>
          <CapitalRotationBoard inflow={capitalInflow} outflow={capitalOutflow} />
        </div>
      </TerminalPanel>
      <div className={`data-screen-news-stack${livePanelClass}`}>
        <TerminalPanel title="实时资讯" subtitle={`${realtimeNews.length} 条资讯 · 持续更新`} ariaLabel="实时资讯" className="data-screen-panel data-screen-watchlist data-screen-news-panel">
          <div className="data-screen-news-panel-layout">
            <section className="data-screen-news-feed"><h3>实时资讯 <small>{realtimeNews.length} 条</small></h3><div className="data-screen-news-grid">{realtimeNews.length ? realtimeNews.map((item) => { const confidence = Number(item.impact_confidence); const confidenceLabel = Number.isFinite(confidence) ? `可信度 ${Math.round(confidence * 100)}%` : "可信度待确认"; return <article key={item.event_id} className={`data-screen-news-card ${item.urgency === "breaking" ? "is-breaking" : ""}`}><time>{formatTime(item.occurred_at)}</time><b>{item.headline}</b><span>{item.affected_symbols.length ? item.affected_symbols.slice(0, 2).join(" · ") : item.themes.slice(0, 2).join(" · ") || "市场"}</span><span className="data-screen-news-tags"><small className="data-screen-news-tag data-screen-news-tag-urgency">{item.urgency === "breaking" ? "突发" : item.urgency === "tracking" ? "跟踪" : "资讯"}</small><small className={`data-screen-news-tag data-screen-news-tag-${item.verification_state}`}>{newsVerificationLabel(item.verification_state)}</small><small className="data-screen-news-tag data-screen-news-tag-confidence">{confidenceLabel}</small><small className={`data-screen-news-tag data-screen-news-tag-${item.impact_direction}`}>{newsImpactLabel(item.impact_direction)}</small></span></article>; }) : <div className="data-screen-empty">暂无已核验实时资讯</div>}</div></section>
            <div className="data-screen-news-signal-pair" aria-label="实时选股命中">
              <section className="data-screen-news-signal-column data-screen-news-quant-column" role="region" aria-label="量化命中">
                <h3>量化命中 <small>{quantCandidates.length ? `${quantCandidates.length} 只` : "暂无命中"}</small></h3>
                <ContinuousRail items={quantCandidates} loopThreshold={2} className="data-screen-news-signal-rail" itemKey={(candidate) => candidate.symbol}>
                  {(candidate) => <button type="button" className={`data-screen-news-signal-row data-screen-news-quant-row${quantHotSymbols.has(candidate.symbol) ? " is-new" : ""}`} onClick={() => onOpenAShare?.(candidate.symbol)}><span><b>{candidate.name}</b><small>{candidate.symbol} · {candidate.model}</small></span><strong>{candidate.strategy_score}</strong><em>{candidate.status === "alert" ? "触发" : candidate.status === "watch" ? "观察" : candidate.status === "pending_trigger" ? "待确认" : "过滤"}</em></button>}
                </ContinuousRail>
              </section>
              <section className="data-screen-news-signal-column data-screen-news-late-column" role="region" aria-label="尾盘选股">
                <h3>尾盘选股 <small>{lateSession?.candidate_count ? `${lateSession.candidate_count} 只` : "暂无命中"}</small></h3>
                <ContinuousRail items={lateSession?.candidates ?? []} loopThreshold={2} className="data-screen-news-signal-rail" itemKey={(candidate) => candidate.quote.symbol}>
                  {(candidate) => <button type="button" className="data-screen-news-signal-row data-screen-news-late-row" onClick={() => onOpenAShare?.(candidate.quote.symbol)}><span><b>{candidate.quote.name}</b><small>{candidate.quote.symbol} · {candidate.behavior_tags[0] || "规则通过"}</small></span><strong className={toneClass(Number(candidate.quote.change_percent) >= 0 ? "up" : "down")}>{signed(Number(candidate.quote.change_percent))}</strong><em>量比 {candidate.quote.volume_ratio || "--"}</em></button>}
                </ContinuousRail>
              </section>
            </div>
          </div>
        </TerminalPanel>
        <TerminalPanel title="板块广度与主线" subtitle={`${topicSectors.length} 个板块`} ariaLabel="板块广度与主线" className="data-screen-panel data-screen-sector-breadth-panel">
          <div className="data-screen-sector-breadth-list">{topicSectors.length ? topicSectors.map((sector) => <button key={sector.sector_id} type="button" className={`data-screen-sector-breadth-row ${toneClass(sector.tone)}${sectorHotIds.has(sector.sector_id) ? " is-updated" : ""}`} onClick={() => onOpenAShare?.(sector.sector_id)}><b>{sector.name}</b><span>{sector.leaderName || "领涨股暂缺"}</span><strong>{signed(Number(sector.change_percent))}</strong><small>上涨 {sector.rising_count} · 下跌 {sector.falling_count} · 成交 {displayNumber(Number(sector.amount_yi), 1)}亿</small></button>) : <span className="data-screen-inline-empty">暂无已验证板块数据</span>}</div>
        </TerminalPanel>
        <TerminalPanel title="行业资金流向" subtitle={sectorFlowItems.length ? `${sectorFlowItems.length} 条 · 持续滚动` : "等待真实资金数据"} ariaLabel="行业资金流向" className="data-screen-panel data-screen-sector-flow-panel data-screen-sector-flow-tape-panel">
          <div className="data-screen-sector-flow-tape" role="list">
            {sectorFlowItems.length ? <div className="data-screen-sector-flow-track"><ContinuousRail items={sectorFlowItems} loopThreshold={0} loopCopies={2} className="data-screen-sector-flow-vertical-rail" itemKey={(flow) => flow.code}>
              {(flow) => <div role="listitem" className={`data-screen-sector-flow-item ${toneClass(flow.tone)}`}>
                <span className="data-screen-sector-flow-name"><b>{flow.name}</b><small>{flow.code}</small></span>
                <strong>{flow.net === null || flow.net === undefined ? "--" : `${flow.net >= 0 ? "+" : ""}${flow.net.toFixed(2)}亿`}</strong>
                <span className="data-screen-sector-flow-detail">主力 {flow.largeNet === null ? "--" : `${flow.largeNet >= 0 ? "+" : ""}${flow.largeNet.toFixed(2)}亿`} · 超大 {flow.superNet === null ? "--" : `${flow.superNet >= 0 ? "+" : ""}${flow.superNet.toFixed(2)}亿`}</span>
              </div>}
            </ContinuousRail></div> : <span className="data-screen-inline-empty">暂无有效行业资金数据</span>}
          </div>
        </TerminalPanel>
      </div>
    </div>
    {fullscreen && <button className="data-screen-exit-hint" type="button" onClick={() => void toggleFullscreen()}><X size={14} /> 退出全屏</button>}
  </main>;
}
