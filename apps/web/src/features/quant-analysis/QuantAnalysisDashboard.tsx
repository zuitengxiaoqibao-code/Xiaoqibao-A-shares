import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EChartsOption } from "echarts";
import {
  Activity, AlertTriangle, BarChart3, Database, RadioTower, ShieldAlert,
} from "lucide-react";

import type { BacktestResult } from "../backtest/types";
import type { FirstLimitUpBoard, FirstLimitUpCandidate } from "../first-limit-up/types";
import type { AShareInstrument, InstrumentSearchResponse } from "../stock-cockpit/types";
import { KronosForecastPanel } from "./KronosForecastPanel";
import { QuantInstrumentSelector } from "./QuantInstrumentSelector";
import { QuantLiveStatusBar } from "./QuantLiveStatusBar";
import { QuantChart } from "./QuantChart";
import { ShortTermStrategyWorkbench } from "./ShortTermStrategyWorkbench";
import { QuantShadowLedgerPanel } from "./QuantShadowLedgerPanel";
import { QuantResearchIntelligencePanel } from "./QuantResearchIntelligencePanel";
import { TdxFormulaPanel } from "./TdxFormulaPanel";
import { WalkForwardEvidenceStrip } from "./WalkForwardEvidenceStrip";
import { StockEventKline } from "../stock-timeline/StockEventKline";
import { DataWatermarkStrip } from "../../shared/evidence/DataWatermarkStrip";
import { RealtimeAIInsight, type RealtimeAIInsightPayload } from "../../shared/RealtimeAIInsight";
import { buildFactorOption } from "../../shared/visualization/chartOptions";
import { chartTheme } from "../../shared/visualization/chartTheme";
import type { StockTimelineLoader } from "../stock-timeline/types";
import { useQuantLiveResource } from "./useQuantLiveRefresh";
import { retainReadyStrategySnapshot } from "./strategySnapshot";
import { useRealtimeFallbackTick, useRealtimeState, useRealtimeSubscription } from "../../shared/realtime/RealtimeProvider";
import { backtestFactorRadar, equityPoints, factorRadar, signalMetrics } from "./metrics";
import { shanghaiDay } from "../../shared/tradingDayContext";
import type {
  DecisionJournalCreator,
  DecisionJournalLoader,
  IntradayTick,
  KronosForecastResponse,
  QuantForecastLoader,
  QuantCalibrationLoader,
  QuantResearchLoader,
  QuantStrategyLoader,
  QuantShadowAnalyticsLoader,
  QuantShadowLoader,
  QuantTickLoader,
  QuantWalkForwardLoader,
  TdxFormulaLoader,
} from "./types";

type Props = {
  loadBoard: () => Promise<FirstLimitUpBoard>;
  refreshBoard?: () => Promise<FirstLimitUpBoard>;
  loadTicks: QuantTickLoader;
  runBacktest: (symbol: string, signal?: AbortSignal) => Promise<BacktestResult>;
  loadKronosForecast?: QuantForecastLoader;
  loadQuantStrategy?: QuantStrategyLoader;
  loadQuantShadowDecisions?: QuantShadowLoader;
  loadQuantShadowAnalytics?: QuantShadowAnalyticsLoader;
  loadQuantCalibration?: QuantCalibrationLoader;
  loadQuantResearch?: QuantResearchLoader;
  loadDecisionJournal?: DecisionJournalLoader;
  createDecisionJournal?: DecisionJournalCreator;
  loadTdxFormula?: TdxFormulaLoader;
  loadTimeline?: StockTimelineLoader;
  loadWalkForward?: QuantWalkForwardLoader;
  selectedSymbol?: string | null;
  searchInstruments?: (query: string) => Promise<InstrumentSearchResponse>;
  onSelectSymbol?: (symbol: string) => void;
};

const gridColor = chartTheme.gridColor;
const axisColor = chartTheme.mutedTextColor;
const gold = chartTheme.warningColor;
const cyan = chartTheme.liveColor;
const magenta = chartTheme.eventColors.risk;

function panelOption(): Pick<EChartsOption, "animation" | "textStyle"> {
  return {
    animation: false,
    textStyle: { color: chartTheme.textColor, fontFamily: chartTheme.fontFamily },
  };
}

function timeLabel(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(new Date(value));
}

function finiteNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function percentText(value: string | number | null | undefined): string {
  const parsed = finiteNumber(value);
  return parsed === null ? "--" : `${(parsed * 100).toFixed(1)}%`;
}

function backtestSampleLabel(result: BacktestResult): string {
  if (result.evidence?.sample_status === "segmented") return "样本外已验证";
  if (result.evidence?.sample_status === "descriptive") return "描述性样本";
  if (result.evidence?.sample_status === "insufficient") return "样本不足";
  return result.metrics.closed_trade_count ? "可计算" : "不足";
}

export function tickOption(ticks: IntradayTick[]): EChartsOption {
  return {
    ...panelOption(),
    grid: [{ left: 52, right: 24, top: 20, height: "52%" }, { left: 52, right: 24, top: "73%", height: "14%" }],
    tooltip: { trigger: "axis", backgroundColor: chartTheme.tooltipBackgroundColor, borderColor: cyan, textStyle: { color: chartTheme.textColor } },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1], filterMode: "none", throttle: 80 },
      { type: "slider", xAxisIndex: [0, 1], bottom: 2, height: 14, borderColor: gridColor, fillerColor: "rgba(52,214,255,.16)", handleStyle: { color: cyan }, textStyle: { color: axisColor }, dataBackground: { lineStyle: { color: "rgba(99,117,138,.45)" }, areaStyle: { color: "rgba(99,117,138,.08)" } } },
    ],
    xAxis: [
      { type: "category", gridIndex: 0, data: ticks.map((item) => timeLabel(item.observed_at)), axisLine: { lineStyle: { color: gridColor } }, axisLabel: { color: axisColor, hideOverlap: true }, axisTick: { show: false } },
      { type: "category", gridIndex: 1, data: ticks.map((item) => timeLabel(item.observed_at)), axisLine: { lineStyle: { color: gridColor } }, axisLabel: { show: false }, axisTick: { show: false } },
    ],
    yAxis: [
      { type: "value", scale: true, gridIndex: 0, splitLine: { lineStyle: { color: gridColor } }, axisLabel: { color: axisColor } },
      { type: "value", gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
    ],
    series: [
      { name: "价格", type: "line", data: ticks.map((item) => Number(item.price)), xAxisIndex: 0, yAxisIndex: 0, symbol: "none", smooth: 0.2, lineStyle: { width: 2, color: cyan, shadowBlur: 8, shadowColor: cyan }, areaStyle: { color: "rgba(52,214,255,.08)" } },
      { name: "成交量", type: "bar", data: ticks.map((item) => Number(item.volume)), xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: (params: { dataIndex: number }) => Number(ticks[params.dataIndex]?.change_percent) >= 0 ? chartTheme.upColor : chartTheme.downColor } },
    ],
  };
}

function backtestOption(backtest: BacktestResult): EChartsOption {
  const points = equityPoints(backtest);
  return {
    ...panelOption(),
    grid: { left: 58, right: 28, top: 30, bottom: 38 },
    legend: { top: 0, right: 8, textStyle: { color: axisColor }, data: ["权益", "回撤"] },
    tooltip: { trigger: "axis", backgroundColor: chartTheme.tooltipBackgroundColor, borderColor: gold, textStyle: { color: chartTheme.textColor } },
    xAxis: { type: "category", data: points.map((item) => item.date), axisLine: { lineStyle: { color: gridColor } }, axisLabel: { color: axisColor, hideOverlap: true } },
    yAxis: [
      { type: "value", scale: true, splitLine: { lineStyle: { color: gridColor } }, axisLabel: { color: axisColor } },
      { type: "value", max: 0, min: (value: { min: number }) => Math.min(-5, Math.floor(value.min)), splitLine: { show: false }, axisLabel: { color: magenta, formatter: "{value}%" } },
    ],
    series: [
      { name: "权益", type: "line", data: points.map((item) => item.equity), symbol: "none", lineStyle: { color: gold, width: 2 }, areaStyle: { color: "rgba(244,199,106,.08)" } },
      { name: "回撤", type: "line", yAxisIndex: 1, data: points.map((item) => item.drawdown), symbol: "none", lineStyle: { color: magenta, width: 1.5 }, areaStyle: { color: "rgba(255,92,138,.08)" } },
    ],
  };
}

function candidatesFrom(board: FirstLimitUpBoard | null): FirstLimitUpCandidate[] {
  if (!board) return [];
  const values = new Map<string, FirstLimitUpCandidate>();
  for (const candidate of board.today) values.set(candidate.symbol, candidate);
  for (const candidate of board.pool) values.set(candidate.symbol, candidate);
  return [...values.values()].sort((left, right) => {
    if (left.symbol === board.priority_symbol) return -1;
    if (right.symbol === board.priority_symbol) return 1;
    return Number(right.score) - Number(left.score);
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isBoardSnapshot(value: unknown): value is FirstLimitUpBoard {
  return isRecord(value)
    && typeof value.as_of === "string"
    && Array.isArray(value.today)
    && Array.isArray(value.pool);
}

function isTickSnapshot(value: unknown, symbol: string | null): value is IntradayTick[] {
  return Array.isArray(value) && value.every((item) => (
    isRecord(item)
    && typeof item.symbol === "string"
    && (!symbol || item.symbol === symbol)
    && typeof item.observed_at === "string"
  ));
}

function hasMatchingSymbol(value: unknown, symbol: string | null): value is Record<string, unknown> {
  return Boolean(symbol) && isRecord(value) && value.symbol === symbol;
}

function isStrategySnapshot(value: unknown): value is Awaited<ReturnType<QuantStrategyLoader>> {
  return isRecord(value)
    && value.formula_version === "a-share-short-strategy-v2.0"
    && typeof value.as_of === "string"
    && Array.isArray(value.candidates);
}

function isShadowRecords(value: unknown): value is Awaited<ReturnType<QuantShadowLoader>> {
  return Array.isArray(value) && value.every((item) => (
    isRecord(item)
    && typeof item.decision_id === "string"
    && typeof item.symbol === "string"
    && typeof item.frozen_at === "string"
    && Array.isArray(item.outcomes)
  ));
}

function isDecisionJournal(value: unknown): value is Awaited<ReturnType<DecisionJournalLoader>> {
  return Array.isArray(value) && value.every((item) => (
    isRecord(item)
    && typeof item.entry_id === "string"
    && typeof item.symbol === "string"
    && typeof item.action === "string"
    && typeof item.recorded_at === "string"
  ));
}

export function QuantAnalysisDashboard({ loadBoard, refreshBoard, loadTicks, runBacktest, loadKronosForecast, loadQuantStrategy, loadQuantResearch, loadQuantShadowDecisions, loadQuantShadowAnalytics, loadQuantCalibration, loadDecisionJournal, createDecisionJournal, loadTdxFormula, loadTimeline, loadWalkForward, selectedSymbol, searchInstruments, onSelectSymbol }: Props) {
  const cacheDay = shanghaiDay(new Date());
  const [selected, setSelected] = useState<string | null>(selectedSymbol ?? null);
  const [selectedIdentity, setSelectedIdentity] = useState<AShareInstrument | null>(null);
  const emptyRefreshAttempted = useRef(false);
  const boardLoader = useCallback(async () => {
    let value = await loadBoard();
    if (value.status === "empty" && refreshBoard && !emptyRefreshAttempted.current) {
      emptyRefreshAttempted.current = true;
      try {
        value = await refreshBoard();
      } catch {
        // Keep the verified read-only result when the active scan source is unavailable.
      }
    }
    return value;
  }, [loadBoard, refreshBoard]);
  const boardResource = useQuantLiveResource({
    loader: boardLoader,
    intervalMs: 30_000,
    errorMessage: "首次涨停候选数据暂不可用",
    polling: false,
    cache: { key: "quant-board", day: cacheDay, validate: isBoardSnapshot },
  });
  const board = boardResource.data;

  const candidates = useMemo(() => candidatesFrom(board), [board]);
  useEffect(() => {
    if (selectedSymbol) {
      setSelected(selectedSymbol);
      return;
    }
    if (!candidates.length) {
      if (!selected) setSelected(null);
      return;
    }
    if (!selected) {
      setSelected(candidates[0].symbol);
    }
  }, [candidates, selected, selectedSymbol]);
  const candidate = candidates.find((item) => item.symbol === selected) ?? null;
  const selectedName = candidate?.name ?? (selectedIdentity?.symbol === selected ? selectedIdentity.name : null);
  const selectSymbol = useCallback((symbol: string, identity?: AShareInstrument) => {
    setSelected(symbol);
    setSelectedIdentity(identity ?? null);
    onSelectSymbol?.(symbol);
  }, [onSelectSymbol]);
  useEffect(() => {
    if (!selected || candidate || selectedIdentity?.symbol === selected || !searchInstruments) return;
    let active = true;
    void searchInstruments(selected).then((response) => {
      if (!active) return;
      const identity = response.items.find((item) => item.symbol === selected);
      if (identity) setSelectedIdentity(identity);
    }).catch(() => {
      // Keep the verified symbol usable when the identity directory is temporarily unavailable.
    });
    return () => { active = false; };
  }, [candidate, searchInstruments, selected, selectedIdentity?.symbol]);
  const tickLoader = useCallback(
    () => selected ? loadTicks(selected) : Promise.resolve([]),
    [loadTicks, selected],
  );
  const tickResource = useQuantLiveResource({
    loader: tickLoader,
    intervalMs: 1_000,
    enabled: Boolean(selected),
    errorMessage: "盘中 TICK 归档暂不可用",
    polling: false,
    cache: {
      key: `quant-ticks:${selected ?? "none"}`,
      day: cacheDay,
      validate: (value): value is IntradayTick[] => isTickSnapshot(value, selected),
    },
  });
  const ticks = useMemo(
    () => (tickResource.data ?? []).filter((item) => item.symbol === selected),
    [selected, tickResource.data],
  );
  const strategyLoader = useCallback(
    () => loadQuantStrategy
      ? loadQuantStrategy(12)
      : Promise.reject(new Error("quant strategy disabled")),
    [loadQuantStrategy],
  );
  const strategyResource = useQuantLiveResource({
    loader: strategyLoader,
    // The realtime snapshot stream carries strategy updates. HTTP polling is
    // a deliberately slower fallback so a candidate scan is never restarted
    // by a five-second full-dashboard request.
    intervalMs: 30_000,
    enabled: Boolean(loadQuantStrategy),
    polling: false,
    errorMessage: "短线策略数据暂不可用",
    mergeData: retainReadyStrategySnapshot,
    initialDelayMs: 250,
    cache: { key: "quant-strategy:12", day: cacheDay, validate: isStrategySnapshot },
  });
  const strategyDashboard = strategyResource.data;
  const strategyRef = useRef(strategyDashboard);
  strategyRef.current = strategyDashboard;
  const strategyStreamState = useRealtimeState();
  const realtimeFallbackTick = useRealtimeFallbackTick();
  const [realtimeAIInsight, setRealtimeAIInsight] = useState<RealtimeAIInsightPayload | null>(null);
  useRealtimeSubscription<NonNullable<typeof strategyDashboard>>("quant_strategy", (event) => {
        if (!loadQuantStrategy) return;
        const incoming = event.payload;
        if (!incoming || incoming.formula_version !== "a-share-short-strategy-v2.0") return;
        const current = strategyRef.current;
        if (current && current.as_of === incoming.as_of && Date.parse(incoming.generated_at) <= Date.parse(current.generated_at)) return;
        strategyResource.acceptExternal(incoming);
  });
  useRealtimeSubscription("market_overview", () => {
    if (selected) void tickResource.refreshNow();
    void boardResource.refreshNow();
  });
  useRealtimeSubscription<RealtimeAIInsightPayload>("ai_analysis", (event) => {
        if (event.payload?.kind === "quant_strategy") setRealtimeAIInsight(event.payload);
  });
  useEffect(() => {
    if (realtimeFallbackTick === 0) return;
    if (selected) void tickResource.refreshNow();
    void boardResource.refreshNow();
  }, [boardResource.refreshNow, realtimeFallbackTick, selected, tickResource.refreshNow]);
  const shadowLoader = useCallback(
    () => loadQuantShadowDecisions ? loadQuantShadowDecisions(50) : Promise.resolve([]),
    [loadQuantShadowDecisions],
  );
  const shadowResource = useQuantLiveResource({
    loader: shadowLoader,
    intervalMs: 60_000,
    enabled: Boolean(loadQuantShadowDecisions),
    polling: false,
    errorMessage: "策略影子账本暂不可用",
    initialDelayMs: 1_800,
    cache: { key: "quant-shadow:50", day: cacheDay, validate: isShadowRecords },
  });
  const shadowAnalyticsLoader = useCallback(
    () => loadQuantShadowAnalytics ? loadQuantShadowAnalytics(5) : Promise.reject(new Error("shadow analytics disabled")),
    [loadQuantShadowAnalytics],
  );
  const shadowAnalyticsResource = useQuantLiveResource({
    loader: shadowAnalyticsLoader,
    intervalMs: 60_000,
    enabled: Boolean(loadQuantShadowAnalytics),
    polling: false,
    errorMessage: "评分校准统计暂不可用",
    initialDelayMs: 2_200,
    cache: {
      key: "quant-shadow-analytics:5",
      day: cacheDay,
      validate: (value): value is Awaited<ReturnType<QuantShadowAnalyticsLoader>> => (
        isRecord(value) && typeof value.generated_at === "string" && Array.isArray(value.buckets)
      ),
    },
  });
  const calibrationLoader = useCallback(
    () => loadQuantCalibration ? loadQuantCalibration(5) : Promise.reject(new Error("quant calibration disabled")),
    [loadQuantCalibration],
  );
  const calibrationResource = useQuantLiveResource({
    loader: calibrationLoader,
    intervalMs: 300_000,
    enabled: Boolean(loadQuantCalibration),
    polling: false,
    errorMessage: "量化走样校准报告暂不可用",
    initialDelayMs: 2_600,
    cache: {
      key: "quant-calibration:5",
      day: cacheDay,
      validate: (value): value is Awaited<ReturnType<QuantCalibrationLoader>> => (
        isRecord(value) && typeof value.generated_at === "string" && Array.isArray(value.splits)
      ),
    },
  });
  const decisionJournalLoader = useCallback(
    () => loadDecisionJournal ? loadDecisionJournal(50) : Promise.resolve([]),
    [loadDecisionJournal],
  );
  const decisionJournalResource = useQuantLiveResource({
    loader: decisionJournalLoader,
    intervalMs: 60_000,
    enabled: Boolean(loadDecisionJournal),
    polling: false,
    errorMessage: "个人复盘日志暂不可用",
    initialDelayMs: 1_800,
    cache: { key: "quant-decision-journal:50", day: cacheDay, validate: isDecisionJournal },
  });
  const refreshDecisionJournal = decisionJournalResource.refreshNow;
  const appendDecisionJournal = useCallback(async (request: Parameters<DecisionJournalCreator>[0]) => {
    if (!createDecisionJournal) return;
    await createDecisionJournal(request);
    await refreshDecisionJournal();
  }, [createDecisionJournal, refreshDecisionJournal]);
  const backtestLoader = useCallback(
    (signal?: AbortSignal) => selected ? runBacktest(selected, signal) : Promise.reject(new Error("backtest target unavailable")),
    [runBacktest, selected],
  );
  const backtestResource = useQuantLiveResource({
    loader: backtestLoader,
    intervalMs: 300_000,
    enabled: Boolean(selected),
    polling: false,
    errorMessage: "历史回测暂不可用",
    initialDelayMs: 600,
    cache: {
      key: `quant-backtest:${selected ?? "none"}`,
      day: cacheDay,
      validate: (value): value is BacktestResult => hasMatchingSymbol(value, selected),
    },
  });
  const walkForwardLoader = useCallback(
    (signal?: AbortSignal) => selected && loadWalkForward
      ? loadWalkForward(selected, signal)
      : Promise.reject(new Error("walk-forward target unavailable")),
    [loadWalkForward, selected],
  );
  const walkForwardResource = useQuantLiveResource({
    loader: walkForwardLoader,
    intervalMs: 300_000,
    enabled: Boolean(selected && loadWalkForward),
    polling: false,
    errorMessage: "样本外验证暂不可用",
    initialDelayMs: 850,
    cache: {
      key: `quant-walk-forward:${selected ?? "none"}`,
      day: cacheDay,
      validate: (value): value is Awaited<ReturnType<QuantWalkForwardLoader>> => hasMatchingSymbol(value, selected),
    },
  });
  const forecastLoader = useCallback(
    () => selected && loadKronosForecast
      ? loadKronosForecast(selected, undefined, 20)
      : Promise.reject(new Error("forecast target unavailable")),
    [loadKronosForecast, selected],
  );
  const forecastResource = useQuantLiveResource({
    loader: forecastLoader,
    intervalMs: 300_000,
    enabled: Boolean(selected && loadKronosForecast),
    polling: false,
    errorMessage: "价格路径预测暂不可用",
    initialDelayMs: 1_100,
    cache: {
      key: `quant-kronos:${selected ?? "none"}:latest`,
      day: cacheDay,
      validate: (value): value is KronosForecastResponse => hasMatchingSymbol(value, selected),
    },
  });

  const latestTick = ticks.at(-1) ?? null;
  const latestPrice = finiteNumber(latestTick?.price);
  const latestChangePercent = finiteNumber(latestTick?.change_percent);
  const candidatePe = finiteNumber(candidate?.pe_ttm);
  const candidatePullback = finiteNumber(candidate?.pullback_pct);
  const selectedBacktest = backtestResource.data?.symbol === selected ? backtestResource.data : null;
  const selectedForecast = forecastResource.data?.symbol === selected ? forecastResource.data : null;
  const strategyCandidate = strategyDashboard?.candidates.find((item) => item.symbol === selected) ?? null;
  const tickEmptyMessage = !candidate
    ? selected ? tickResource.status === "loading" ? "正在读取盘中 TICK" : tickResource.error || "暂无已归档盘中 TICK" : "等待分析标的"
    : tickResource.status === "loading"
      ? "正在读取盘中 TICK"
      : tickResource.error || "暂无已归档盘中 TICK";
  const metrics = signalMetrics(candidate, selectedBacktest, strategyCandidate);
  const radar = candidate
    ? factorRadar(candidate)
    : selectedBacktest
      ? backtestFactorRadar(selectedBacktest, strategyCandidate)
      : null;
  const equity = equityPoints(selectedBacktest);

  return <main className="terminal-page quant-analysis-page" aria-label="首次涨停量化分析">
    <header className="quant-hero">
      <div><p className="quant-kicker"><RadioTower size={15} />FIRST LIMIT-UP / QUANT LAB</p><h1>量化分析仪表盘</h1><p>把盘中快照、规则因子与历史回测放进同一张证据面板；这里只做观察，不生成自动交易指令。</p></div>
      <QuantInstrumentSelector symbol={selected} name={selectedName} candidates={candidates} candidate={candidate} boardAsOf={board?.as_of} search={searchInstruments} onSelect={selectSymbol} />
    </header>

    <QuantLiveStatusBar
      board={board}
      boardStatus={boardResource.status}
      boardLastSuccessAt={boardResource.lastSuccessAt}
      latestTick={latestTick}
      tickStatus={tickResource.status}
      strategy={strategyDashboard}
      strategyStatus={strategyResource.status}
      strategyEnabled={Boolean(loadQuantStrategy)}
      strategyStreamState={strategyStreamState}
    />
    {strategyDashboard && <DataWatermarkStrip
      status={strategyDashboard.status}
      tradeDate={strategyDashboard.as_of}
      observedAt={strategyDashboard.market_observed_at}
      generatedAt={strategyDashboard.generated_at}
      sourceCount={strategyDashboard.sources.length}
      sampleCount={strategyDashboard.candidate_funnel?.stages.find((item) => item.key === "universe")?.count ?? null}
      totalCount={strategyDashboard.evidence_ledger?.[0]?.total_count ?? null}
      coveragePercent={strategyDashboard.evidence_ledger?.[0]?.coverage_percent ?? null}
      refreshState={strategyDashboard.refresh_state ?? "ready"}
      limitations={[...strategyDashboard.missing_data, ...strategyDashboard.warnings]}
    />}

    {loadTimeline && selected && <section className="tdx-research-overview" role="region" aria-label="通达信式研究总览">
      <header className="tdx-research-overview-header"><div><p>TDX STYLE / PRICE EVIDENCE</p><h2>{selectedName ?? selected} · 研究总览</h2></div><span>红涨 · 绿跌 · 灰色代表数据未接入</span></header>
      <div className="tdx-quote-strip">
        <div><span>当前标的</span><strong>{selected}</strong><small>{selectedName ?? "名称待验证"}</small></div>
        <div><span>首次涨停日期</span><strong>{candidate?.limit_up_date ?? "--"}</strong><small>{candidate ? "候选规则已关联" : "未进入候选池"}</small></div>
        <div><span>PE(TTM)</span><strong className={candidatePe !== null && candidatePe > 0 ? "up" : "muted"}>{candidatePe === null ? "--" : candidatePe.toFixed(2)}</strong><small>仅展示已验证估值</small></div>
        <div><span>当前回撤</span><strong className={candidatePullback !== null && candidatePullback > 0 ? "down" : "muted"}>{candidatePullback === null ? "--" : `${(candidatePullback * 100).toFixed(1)}%`}</strong><small>相对首次涨停收盘</small></div>
        <div><span>规则状态</span><strong className={candidate?.selection_status === "qualified" ? "up" : "muted"}>{candidate?.selection_status === "qualified" ? "已通过" : candidate ? "待核验" : "无候选规则"}</strong><small>{candidate?.stage ?? "custom"}</small></div>
      </div>
      <StockEventKline symbol={selected} load={loadTimeline} />
    </section>}

    {boardResource.status === "error" && !board && <div className="quant-page-error"><ShieldAlert size={18} />首次涨停候选数据暂不可用</div>}
    {board && !selected && <div className="quant-page-error"><Database size={18} />当前没有可供量化分析的股票</div>}

    <div className="quant-quadrants" aria-busy={boardResource.status === "loading"}>
      <section className="quant-panel quant-tick-panel" role="region" aria-label="高频 TICK 分时">
        <header><div><span>Q1 / LIVE TRACE</span><h2>高频 TICK 分时</h2></div><div className={`quant-feed-state ${latestTick?.quality ?? "blocked"}`}><i />{latestTick ? latestTick.quality === "ready" ? "归档在线" : "数据降级" : "等待采样"}</div></header>
        {latestTick && <div className="quant-price-overlay"><strong>{latestPrice === null ? "--" : latestPrice.toFixed(2)}</strong><span className={latestChangePercent === null ? "unavailable" : latestChangePercent >= 0 ? "up" : "down"}>{latestChangePercent === null ? "数据不可用" : `${latestChangePercent >= 0 ? "+" : ""}${latestChangePercent.toFixed(2)}%`}</span><small>{timeLabel(latestTick.observed_at)} · {latestTick.source}</small></div>}
        {ticks.length > 0 ? <QuantChart option={tickOption(ticks)} ariaLabel={`${selectedName ?? selected ?? "当前股票"}盘中价格和成交量`} /> : <div className="quant-empty"><Activity size={24} /><b>{tickEmptyMessage}</b><p>系统不会用随机走势填充图表；进入盘中监测名单后才会累积采样点。</p></div>}
      </section>

      <section className="quant-panel quant-signal-panel" role="region" aria-label="信号引擎">
        <header><div><span>Q2 / SIGNAL CORE</span><h2>信号引擎</h2></div><BarChart3 size={18} /></header>
        <div className="quant-signal-list">
          {metrics.map((metric) => <div className={`quant-signal-row ${metric.tone}`} key={metric.key}><div><b>{metric.label}</b><small>{metric.detail}</small></div><div className="quant-signal-value"><strong>{metric.value}</strong><span><i style={{ width: `${metric.barValue}%` }} /></span></div></div>)}
        </div>
      </section>

      <section className="quant-panel quant-radar-panel" role="region" aria-label="量化因子雷达">
        <header><div><span>Q3 / FACTOR ARRAY</span><h2>量化因子雷达</h2></div><small>{radar ? `证据覆盖 ${radar.verifiedCount}/6` : "等待证据"}</small></header>
        {radar ? <><QuantChart option={buildFactorOption({ indicators: radar.indicators.map((name) => ({ name, max: 100 })), values: radar.values, name: candidate ? "规则因子" : "历史回测因子" })} ariaLabel={`${selectedName ?? selected ?? "当前股票"}${candidate ? "首次涨停规则" : "历史回测"}因子雷达`} /><p className="quant-panel-note">{candidate ? "雷达值由 PE、周/月线距低点、回撤阶段、盘整天数和规则分派生；缺失字段保持空缺并计入证据覆盖。" : "历史回测因子由真实闭合交易、波动、回撤、Sharpe 与量化策略综合分派生；未进入首次涨停池也能独立分析。"}</p></> : <div className="quant-empty"><b>{selected ? "正在建立标的因子证据" : "暂无规则因子"}</b><p>{selected ? "优先读取该股票的真实回测与量化策略证据。" : "选择股票后再检查因子证据。"}</p></div>}
      </section>

      <section className="quant-panel quant-backtest-panel" role="region" aria-label="回测风险收益">
        <header><div><span>Q4 / RISK RETURN</span><h2>回测风险收益</h2></div>{selectedBacktest && <small>{selectedBacktest.metrics.closed_trade_count} 笔闭合交易</small>}</header>
        {selectedBacktest && equity.length > 0 ? <><QuantChart option={backtestOption(selectedBacktest)} ariaLabel={`${selectedName ?? selected ?? "当前股票"}历史回测权益和回撤`} /><div className="quant-backtest-stats"><span>总收益<b data-state={finiteNumber(selectedBacktest.total_return) === null ? "unavailable" : "ready"}>{percentText(selectedBacktest.total_return)}</b></span><span>最大回撤<b data-state={finiteNumber(selectedBacktest.max_drawdown) === null ? "unavailable" : "ready"}>{percentText(selectedBacktest.max_drawdown)}</b></span><span>样本状态<b>{backtestSampleLabel(selectedBacktest)}</b></span></div></> : <div className="quant-empty"><AlertTriangle size={24} /><b>{backtestResource.error || "等待历史回测"}</b><p>需要完整日线和闭合交易样本，胜率、赔率与 EV 才会显示。</p></div>}
      </section>

      <KronosForecastPanel forecast={selectedForecast} loading={forecastResource.status === "loading" && !selectedForecast} error={forecastResource.error} />
    </div>

    {loadWalkForward && <WalkForwardEvidenceStrip
      report={walkForwardResource.data?.symbol === selected ? walkForwardResource.data : null}
      loading={walkForwardResource.status === "loading" && !walkForwardResource.data}
      error={walkForwardResource.error}
    />}

    {loadQuantStrategy && <ShortTermStrategyWorkbench
      dashboard={strategyDashboard}
      loading={strategyResource.status === "loading" && !strategyDashboard}
      error={strategyResource.error}
    />}
    {loadQuantResearch && <QuantResearchIntelligencePanel load={loadQuantResearch} />}
    <RealtimeAIInsight insight={realtimeAIInsight} domainLabel="量化分析" />
    {loadQuantShadowDecisions && <QuantShadowLedgerPanel
      records={shadowResource.data ?? []}
      loading={shadowResource.status === "loading" && !shadowResource.data}
      error={shadowResource.error}
      analytics={shadowAnalyticsResource.data}
      analyticsLoading={shadowAnalyticsResource.status === "loading" && !shadowAnalyticsResource.data}
      analyticsError={shadowAnalyticsResource.error}
      calibration={calibrationResource.data}
      journalRecords={decisionJournalResource.data ?? []}
      journalSymbol={selected}
      journalLoading={decisionJournalResource.status === "loading" && !decisionJournalResource.data}
      journalError={decisionJournalResource.error}
      onJournalCreate={createDecisionJournal ? appendDecisionJournal : undefined}
    />}
    <TdxFormulaPanel symbol={selected} load={loadTdxFormula} />
  </main>;
}
