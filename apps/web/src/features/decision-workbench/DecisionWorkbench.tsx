import { AlertTriangle, Bot, ChevronDown, ChevronUp, Clock3, RefreshCw, ShieldAlert, Telescope } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import type { Advice, DecisionPhase, DecisionResponse, Evidence, PhaseSlot } from "./types";
import { beginnerAdviceExplanation } from "./explanation";
import { livePhaseFreshness } from "./freshness";
import { phaseExecutionCopy } from "./phaseExecution";
import { PhaseContextPanel } from "./PhaseContextPanel";

type Props = {
  loadCurrent: () => Promise<DecisionResponse>; loadDate?: (date: string) => Promise<DecisionResponse>;
  selectedSymbol?: string | null; asOf?: string; onAsOfChange?: (date: string) => void; onResolvedAsOf?: (date: string) => void; onReturnLive?: () => void;
  refreshToken?: number; onRefresh?: (reason: "manual" | "poll") => void;
};
const phaseNames: Record<DecisionPhase, string> = { premarket: "盘前研判", intraday: "盘中监测", postclose: "盘后复盘" };
const actionNames: Record<Advice["action"], string> = { observe: "观察", wait: "等待", avoid: "回避", invalidated: "已失效" };
const DEFAULT_VISIBLE_CHANGE_VERSIONS = 3;

function pollingErrorReason(code?: string | null): string {
  if (!code) return "行情更新暂时失败，具体原因尚未确认";
  if (code.includes("timeout")) return "上游行情响应超时";
  if (code === "incomplete_quote_batch_error") return "部分股票行情缺失，完整性检查未通过";
  if (code === "http_status_error") return "上游行情返回异常状态";
  if (code === "unicode_decode_error") return "行情文本解码失败";
  if (code === "value_error") return "行情数据格式不完整";
  return "行情服务暂时不可用";
}

function relevantPollingHealth(
  phase: DecisionPhase,
  marketSession: DecisionResponse["market_session"],
  polling: DecisionResponse["polling"],
  selectedSymbol?: string | null,
) {
  if (phase !== "intraday" || marketSession !== "open") {
    return {
      label: "实时行情", failures: 0, issue: false, reason: "",
      statusText: "当前阶段不检查实时行情",
    };
  }
  const focus = Boolean(selectedSymbol?.trim());
  const label = focus ? "焦点行情" : "全市场行情";
  const failures = focus
    ? polling.consecutive_focus_failures ?? 0
    : polling.consecutive_universe_failures ?? 0;
  const code = focus ? polling.focus_error_code : polling.universe_error_code;
  return {
    label, failures, issue: failures > 0, reason: pollingErrorReason(code),
    statusText: null,
  };
}

function phaseSummary(slot: PhaseSlot, phase: DecisionPhase): string {
  const execution = phaseExecutionCopy(slot.execution, phase);
  if (execution) return execution.label;
  if (slot.phase_status === "empty") return "暂无已验证结果";
  if (slot.phase_status === "blocked") return "已拦截";
  if (slot.phase_status === "partial") return `部分可用 · ${slot.advice.length} 条建议`;
  return `已生成 ${slot.advice.length} 条建议`;
}

function ChangeStream({ slot }: { slot: PhaseSlot }) {
  const [expandedStream, setExpandedStream] = useState<string | null>(null);
  const versions = [...(slot.change_stream ?? [])].sort((left, right) => right.sequence - left.sequence);
  if (versions.length === 0) return null;
  const streamIdentity = versions.map((version) => version.snapshot_id).join(",");
  const expanded = expandedStream === streamIdentity;
  const visibleVersions = expanded ? versions : versions.slice(0, DEFAULT_VISIBLE_CHANGE_VERSIONS);
  return <section className="change-stream" aria-label="盘中变化流">
    <div className="change-stream-heading"><h4>变化流</h4><span>显示 {visibleVersions.length} / 共 {versions.length} 个版本</span></div>
    {visibleVersions.map((version) => <details key={version.snapshot_id}><summary>变化版本 #{version.sequence} · {version.delta_advice.length} 项 · {new Date(version.generated_at).toLocaleTimeString("zh-CN")}</summary><div>{version.delta_advice.length === 0 ? <p>本版本没有建议字段变化</p> : version.delta_advice.map((advice) => <article key={advice.advice_id}><b>{advice.symbol} · {actionNames[advice.action]} · {advice.conclusion}</b><span>变更字段：{advice.changed_fields?.length ? advice.changed_fields.join("、") : "首次记录或未标注字段级变化"}</span><span>前序建议：{advice.previous_advice_id ?? "无（当前记录未提供前序）"}</span><div>{advice.supporting_evidence.length ? advice.supporting_evidence.map((evidence) => <p key={evidence.evidence_id}>触发证据：{evidence.summary}<small>{evidence.source} · {new Date(evidence.observed_at).toLocaleString("zh-CN")}</small></p>) : <p>确定性原因：{advice.risks.join("；") || advice.invalidation_conditions.join("；") || "当前记录未提供具体原因"}</p>}</div></article>)}</div></details>)}
    {versions.length > DEFAULT_VISIBLE_CHANGE_VERSIONS && <button className="change-stream-disclosure" type="button" aria-expanded={expanded} onClick={() => setExpandedStream(expanded ? null : streamIdentity)}>
      {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      {expanded ? "收起早期版本" : `查看更早 ${versions.length - DEFAULT_VISIBLE_CHANGE_VERSIONS} 个版本`}
    </button>}
  </section>;
}

function isLiveQuoteEvidence(evidence: Evidence): boolean {
  if (evidence.evidence_kind === "live_quote") return true;
  return (
    (evidence.evidence_kind === undefined || evidence.evidence_kind === "other")
    && evidence.evidence_id === evidence.snapshot_id
    && evidence.evidence_id.startsWith(`${evidence.source}-`)
  );
}

function currentSupportingEvidence(advice: Advice, phase: DecisionPhase): Evidence[] {
  if (phase !== "intraday") return advice.supporting_evidence;
  const baseline = advice.supporting_evidence.filter((item) => !isLiveQuoteEvidence(item));
  const latestQuote = advice.supporting_evidence
    .filter(isLiveQuoteEvidence)
    .sort((left, right) => Date.parse(right.observed_at) - Date.parse(left.observed_at))[0];
  return latestQuote ? [...baseline, latestQuote] : baseline;
}

function AdvicePanel({ advice, phase }: { advice: Advice; phase: DecisionPhase }) {
  const supportingEvidence = currentSupportingEvidence(advice, phase);
  return <article className="decision-advice"><header><div><span>{advice.horizon === "intraday" ? "短期观察" : "波段观察"}</span><h3>{advice.symbol} · {advice.conclusion}</h3></div><strong>{Math.round(Number(advice.confidence) * 100)}%</strong></header>
    <p className="plain-explanation">{beginnerAdviceExplanation(advice, phase) || "AI 解释不可用，保留确定性结论。"}</p>
    <section className="evidence-band"><h4>支持证据</h4>{supportingEvidence.map((item) => <p key={item.evidence_id}>{item.summary}<small>{item.source} · {new Date(item.observed_at).toLocaleString("zh-CN")}</small></p>)}</section>
    <section className="risk-band"><h4><ShieldAlert size={14} />关键风险</h4>{advice.risks.map((risk) => <p key={risk}>{risk}</p>)}</section>
    <section className="contrary-band"><h4><AlertTriangle size={14} />反向证据</h4>{advice.contrary_evidence.length ? advice.contrary_evidence.map((item) => <p key={item.evidence_id}>{item.summary}</p>) : <p>反向证据：暂无已验证记录</p>}</section>
    <section className="invalidation-band"><h4>失效条件</h4>{advice.invalidation_conditions.map((item) => <p key={item}>{item}</p>)}</section>
    <footer><span>来源时间 {new Date(advice.created_at).toLocaleString("zh-CN")}</span><code>{advice.strategy_version}</code></footer>
  </article>;
}

function PhaseContent({ phase, slot, serverTime, marketSession, polling, selectedSymbol }: { phase: DecisionPhase; slot: PhaseSlot; serverTime: string; marketSession: DecisionResponse["market_session"]; polling: DecisionResponse["polling"]; selectedSymbol?: string | null }) {
  const executionCopy = phaseExecutionCopy(slot.execution, phase);
  if (slot.phase_status === "empty") return <section className="decision-message"><Telescope size={24} /><h2>{executionCopy ? `${phaseNames[phase]}${executionCopy.label}` : selectedSymbol === null ? "尚未选择 A 股，当前不展示单股记录" : selectedSymbol ? `${selectedSymbol} 当前阶段暂无决策快照` : "当前阶段暂无决策快照"}</h2><p>{executionCopy?.detail ?? "等待调度生成已验证的聚合结果，不展示推测数据。"}</p></section>;
  const freshness = livePhaseFreshness({
    phase, marketSession, serverTime, generatedAt: slot.generated_at, selectedSymbol, polling,
  });
  const freshnessScope = freshness.scope === "focus" ? "焦点行情" : "全市场行情";
  const freshnessDetail = freshness.referenceSource === "poll_success"
    ? `${freshnessScope}最近成功于 ${new Date(freshness.referenceAt ?? "").toLocaleString("zh-CN")}`
    : `${freshnessScope}尚无成功轮询；当前建议生成于 ${new Date(freshness.referenceAt ?? "").toLocaleString("zh-CN")}`;
  const pollingHealth = relevantPollingHealth(phase, marketSession, polling, selectedSymbol);
  const pollingStatus = pollingHealth.statusText ?? (pollingHealth.issue
    ? `${pollingHealth.label}异常 · ${pollingHealth.failures} 次`
    : `${pollingHealth.label}正常`);
  const emptyTitle = selectedSymbol === null ? "尚未选择 A 股，当前不展示单股建议" : selectedSymbol ? `${selectedSymbol} 当前阶段暂无已验证建议` : "当前阶段没有可展示建议";
  return <div className="decision-columns"><section>{executionCopy && <div className={`quality-banner execution-${slot.execution?.status}`}><b>{executionCopy.label}</b><span>{executionCopy.detail}</span></div>}<div className={`quality-banner ${slot.phase_status}`}><b>{slot.phase_status === "blocked" ? "决策已拦截" : slot.phase_status === "partial" ? "数据部分可用" : "决策快照就绪"}</b><span>{slot.aggregate_version}</span></div>{pollingHealth.issue && <div className="polling-banner" role="status"><AlertTriangle size={17} /><div><b>{pollingHealth.label}更新暂时失败</b><span>已连续失败 {pollingHealth.failures} 次 · {pollingHealth.reason}</span><small>系统会自动重试；最近有效建议会保留，不会用缺失行情刷新。</small></div></div>}{freshness.status === "stale" && <div className="stale-banner" role="status"><AlertTriangle size={17} /><div><b>行情更新已超过有效时间</b><span>{freshnessDetail}</span><small>最近有效建议会保留，但不会用推测数据刷新。</small></div></div>}<PhaseContextPanel context={slot.context} />{slot.advice.length === 0 && <section className="decision-message compact"><h2>{emptyTitle}</h2><p>保留阶段质量状态，不补造建议。</p></section>}{slot.advice.map((item) => <AdvicePanel key={item.advice_id} advice={item} phase={phase} />)}</section><aside className="decision-rail"><h3>阶段状态</h3><p><Bot size={14} />AI {slot.ai_status === "ready" ? "可用" : slot.ai_status === "unavailable" ? "不可用" : "未调用"}</p><p>质量 {slot.quality}</p><p>{pollingStatus}</p><p>当前观察 {slot.advice.length} · 本次变化 {slot.delta_advice?.length ?? 0}</p><p>变化版本 {slot.delta_version ?? "--"}</p><p>聚合版本 {slot.aggregate_version}</p><ChangeStream slot={slot} /></aside></div>;
}

function selectedSlot(slot: PhaseSlot, symbol?: string | null): PhaseSlot {
  if (symbol === undefined) return slot;
  const advice = slot.advice.filter((item) => item.asset === "a_share" && item.symbol === symbol);
  const evidenceIds = new Set(advice.flatMap((item) => [...item.supporting_evidence, ...item.contrary_evidence]).map((item) => item.evidence_id));
  const deltaAdvice = slot.delta_advice?.filter((item) => item.asset === "a_share" && item.symbol === symbol);
  const context = slot.context ? {
    ...slot.context,
    news: {
      ...slot.context.news,
      events: slot.context.news.events.filter(
        (item) => item.affected_symbols.length === 0 || item.affected_symbols.includes(symbol ?? "")
      ),
    },
  } : undefined;
  return {
    ...slot, advice, evidence: slot.evidence.filter((item) => evidenceIds.has(item.evidence_id)),
    delta_advice: deltaAdvice, context,
    change_stream: slot.change_stream?.map((version) => {
      const versionAdvice = version.delta_advice.filter((item) => item.asset === "a_share" && item.symbol === symbol);
      return { ...version, delta_advice: versionAdvice };
    }).filter((version) => version.delta_advice.length > 0),
  };
}

export function DecisionWorkbench({ loadCurrent, loadDate, selectedSymbol, asOf, onAsOfChange, onResolvedAsOf, onReturnLive, refreshToken = 0, onRefresh }: Props) {
  const [data, setData] = useState<DecisionResponse | null>(null); const [phase, setPhase] = useState<DecisionPhase>("premarket");
  const [internalDate, setInternalDate] = useState(""); const date = asOf ?? internalDate; const [historicalMode, setHistoricalMode] = useState(false); const [error, setError] = useState(""); const [loading, setLoading] = useState(true); const sequence = useRef(0); const manualPhase = useRef(false); const initialLoad = useRef(true); const handledRefresh = useRef(refreshToken);
  const selectDate = useCallback((nextDate: string) => { setInternalDate(nextDate); onAsOfChange?.(nextDate); }, [onAsOfChange]);
  const publishResolvedDate = useCallback((nextDate: string) => { setInternalDate(nextDate); onResolvedAsOf?.(nextDate); }, [onResolvedAsOf]);
  const load = useCallback(async (selectedDate?: string) => { const request = ++sequence.current; setLoading(true); setError(""); try { const next = selectedDate && loadDate ? await loadDate(selectedDate) : await loadCurrent(); if (request !== sequence.current) return; setData(next); if (initialLoad.current || !manualPhase.current) setPhase(next.current_phase); initialLoad.current = false; publishResolvedDate(next.trading_date); } catch (caught) { if (request === sequence.current) setError(caught instanceof Error ? caught.message : "决策链路暂不可用"); } finally { if (request === sequence.current) setLoading(false); } }, [loadCurrent, loadDate, publishResolvedDate]);
  const loadRef = useRef(load); loadRef.current = load;
  useEffect(() => { void loadRef.current(); }, []);
  useEffect(() => { if (refreshToken === handledRefresh.current) return; handledRefresh.current = refreshToken; void load(historicalMode ? date : undefined); }, [date, historicalMode, load, refreshToken]);
  useEffect(() => { if (historicalMode || !data || data.market_session !== "open" || !data.polling.focus_interval_seconds) return; const timer = window.setInterval(() => { if (onRefresh) onRefresh("poll"); else void load(); }, Math.max(1, data.polling.focus_interval_seconds) * 1000); return () => window.clearInterval(timer); }, [data?.market_session, data?.polling.focus_interval_seconds, historicalMode, load, onRefresh]);
  const phases = Object.keys(phaseNames) as DecisionPhase[];
  function selectPhase(item: DecisionPhase, focus = false) { manualPhase.current = true; if (focus) document.getElementById(`decision-tab-${item}`)?.focus(); setPhase(item); }
  function tabKey(event: React.KeyboardEvent, item: DecisionPhase) { const index = phases.indexOf(item); const next = event.key === "ArrowRight" ? phases[(index + 1) % phases.length] : event.key === "ArrowLeft" ? phases[(index - 1 + phases.length) % phases.length] : null; if (next) { event.preventDefault(); selectPhase(next, true); } }
  return <main className="decision-workbench"><header className="decision-header"><div><p className="eyebrow">A 股 · 每日决策工作台</p><h1>今日判断与三阶段跟踪</h1></div><div className="decision-date-controls"><label>交易日期<input aria-label="交易日期" type="date" value={date} onChange={(event) => { setHistoricalMode(true); selectDate(event.target.value); void load(event.target.value); }} /></label>{historicalMode && <button type="button" onClick={() => { setHistoricalMode(false); onReturnLive?.(); void load(); }}><Clock3 size={14} />返回实时</button>}<button type="button" onClick={() => onRefresh ? onRefresh("manual") : void load(historicalMode ? date : undefined)}><RefreshCw size={14} />刷新当前</button></div></header>
    {data && <section className="session-status"><div><Clock3 size={15} /><b>{data.market_session === "open" ? "市场进行中" : "市场已休市"}</b><span>焦点 {data.polling.focus_interval_seconds ?? "--"}s</span></div><div><span>全域 {data.polling.universe_interval_seconds ?? "--"}s</span><span>超时阈值 {data.polling.stale_after_seconds}s</span><span>下次检查 {data.polling.next_check_seconds ?? "--"}s</span></div></section>}
    <div className="phase-tabs" role="tablist">{phases.map((item) => <button id={`decision-tab-${item}`} aria-label={phaseNames[item]} aria-controls={`decision-panel-${item}`} data-phase-state={data?.phases[item].execution?.status ?? data?.phases[item].phase_status ?? "loading"} tabIndex={phase === item ? 0 : -1} key={item} role="tab" aria-selected={phase === item} onKeyDown={(event) => tabKey(event, item)} onClick={() => selectPhase(item)}><span>{phaseNames[item]}</span><small>{data ? phaseSummary(data.phases[item], item) : "正在读取"}</small></button>)}</div>
    {loading && !data && <section className="decision-message" aria-busy="true"><RefreshCw size={22} /><h2>正在读取决策聚合</h2></section>}
    {error && <section className={`decision-error${data ? " decision-error-stale" : ""}`} role="alert"><AlertTriangle size={18} /><p>{data ? `最新研判刷新失败，已保留上次有效研判：${error}` : error}</p><button onClick={() => void load(historicalMode ? date : undefined)}>重试</button></section>}
    {data && <div id={`decision-panel-${phase}`} role="tabpanel" aria-labelledby={`decision-tab-${phase}`}><PhaseContent phase={phase} slot={selectedSlot(data.phases[phase], selectedSymbol)} serverTime={data.server_time} marketSession={data.market_session} polling={data.polling} selectedSymbol={selectedSymbol} /></div>}
  </main>;
}
