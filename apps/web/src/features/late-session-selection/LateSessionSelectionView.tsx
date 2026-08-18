import { Activity, AlertTriangle, CheckCircle2, Clock3, Database, RefreshCw, ShieldAlert, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { loadLateSessionAIAnalysis } from "./api";
import { DailyRefreshStatus } from "../../shared/DailyRefreshStatus";
import { consumeRealtimeStream, type RealtimeStreamState } from "../../shared/realtimeStream";
import type { LateSessionAIAnalysis, LateSessionRuleSettings, LateSessionSelectionLoader, LateSessionSelectionResponse, LoadProgress } from "./types";
import "./lateSessionSelection.css";

const phaseLabel = { pre_screen: "14:30前预筛", live_monitor: "14:30–15:00实时监控", post_close: "15:00收盘冻结" } as const;
const stageLabel = { idle: "等待预计算", precompute: "慢因子预计算", reduce_pool: "全市场缩池", monitor: "候选实时监控", confirm: "稳定性确认", closing_auction: "收盘集合竞价", frozen: "收盘快照已冻结" } as const;
const lifecycleLabel = { strict_passed: "严格通过", near_match: "接近通过", data_pending: "数据待补", invalidated: "已失效" } as const;

function durationLabel(seconds: number) {
  if (seconds < 60) return `${seconds}秒`;
  return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
}

function statusLabel(status: string) {
  return status === "passed" ? "通过" : status === "failed" ? "未通过" : status === "disabled" ? "已停用" : "不可用";
}

function timeValue(value: string) {
  return value.slice(0, 5);
}

function NumericRule({ label, enabled, minimum, maximum, onEnabled, onMinimum, onMaximum, suffix = "" }: {
  label: string;
  enabled: boolean;
  minimum: string | number;
  maximum: string | number;
  onEnabled: (value: boolean) => void;
  onMinimum: (value: string) => void;
  onMaximum: (value: string) => void;
  suffix?: string;
}) {
  return <div className="late-session-rule-editor-row">
    <label className="late-session-rule-toggle"><input type="checkbox" checked={enabled} onChange={(event) => onEnabled(event.target.checked)} /><b>{label}</b></label>
    <div className="late-session-rule-range"><input aria-label={`${label}最小值`} type="number" step="0.01" value={String(minimum)} disabled={!enabled} onChange={(event) => onMinimum(event.target.value)} /><span>至</span><input aria-label={`${label}最大值`} type="number" step="0.01" value={String(maximum)} disabled={!enabled} onChange={(event) => onMaximum(event.target.value)} /><em>{suffix}</em></div>
  </div>;
}

function RuleEditor({ draft, defaultSettings, onChange, onApply, onReset, applying }: {
  draft: LateSessionRuleSettings;
  defaultSettings: LateSessionRuleSettings;
  onChange: (patch: Partial<LateSessionRuleSettings>) => void;
  onApply: () => void;
  onReset: () => void;
  applying: boolean;
}) {
  return <section className="late-session-rule-editor">
    <header><div><p className="eyebrow">CUSTOM FILTER</p><h2><SlidersHorizontal size={18} />自由设定筛选规则</h2><small>当前页面默认使用截图规则；修改后点击应用，后端按真实行情重新计算。</small></div><div className="late-session-rule-editor-actions"><button type="button" onClick={onReset}>恢复默认</button><button type="button" className="primary" onClick={onApply} disabled={applying}>{applying ? "正在筛选…" : "按当前规则筛选"}</button></div></header>
    <div className="late-session-rule-editor-grid">
      <div className="late-session-time-editor"><label className="late-session-rule-toggle"><input type="checkbox" checked={draft.time_enabled} onChange={(event) => onChange({ time_enabled: event.target.checked })} /><b>监控时间</b></label><div><input aria-label="监控开始时间" type="time" value={timeValue(draft.start_time)} disabled={!draft.time_enabled} onChange={(event) => onChange({ start_time: event.target.value })} /><span>至</span><input aria-label="监控结束时间" type="time" value={timeValue(draft.end_time)} disabled={!draft.time_enabled} onChange={(event) => onChange({ end_time: event.target.value })} /></div><small>默认 {timeValue(defaultSettings.start_time)}–{timeValue(defaultSettings.end_time)}</small></div>
      <NumericRule label="涨幅" enabled={draft.change_enabled} minimum={draft.change_min} maximum={draft.change_max} suffix="%" onEnabled={(value) => onChange({ change_enabled: value })} onMinimum={(value) => onChange({ change_min: value })} onMaximum={(value) => onChange({ change_max: value })} />
      <NumericRule label="量比" enabled={draft.volume_ratio_enabled} minimum={draft.volume_ratio_min} maximum={draft.volume_ratio_max} onEnabled={(value) => onChange({ volume_ratio_enabled: value })} onMinimum={(value) => onChange({ volume_ratio_min: value })} onMaximum={(value) => onChange({ volume_ratio_max: value })} />
      <NumericRule label="换手率" enabled={draft.turnover_rate_enabled} minimum={draft.turnover_rate_min} maximum={draft.turnover_rate_max} suffix="%" onEnabled={(value) => onChange({ turnover_rate_enabled: value })} onMinimum={(value) => onChange({ turnover_rate_min: value })} onMaximum={(value) => onChange({ turnover_rate_max: value })} />
      <NumericRule label="总市值" enabled={draft.market_cap_enabled} minimum={draft.market_cap_min} maximum={draft.market_cap_max} suffix="亿元" onEnabled={(value) => onChange({ market_cap_enabled: value })} onMinimum={(value) => onChange({ market_cap_min: value })} onMaximum={(value) => onChange({ market_cap_max: value })} />
      <div className="late-session-count-editor"><label className="late-session-rule-toggle"><input type="checkbox" checked={draft.twenty_day_limit_up_enabled} onChange={(event) => onChange({ twenty_day_limit_up_enabled: event.target.checked })} /><b>20日涨停次数</b></label><div><input aria-label="20日涨停最小次数" type="number" min="0" step="1" value={draft.twenty_day_limit_up_min} disabled={!draft.twenty_day_limit_up_enabled} onChange={(event) => onChange({ twenty_day_limit_up_min: Number(event.target.value) })} /><span>至</span><input aria-label="20日涨停最大次数" type="number" min="0" step="1" placeholder="不限" value={draft.twenty_day_limit_up_max ?? ""} disabled={!draft.twenty_day_limit_up_enabled} onChange={(event) => onChange({ twenty_day_limit_up_max: event.target.value === "" ? null : Number(event.target.value) })} /><em>次</em></div></div>
      <div className="late-session-relation-editor"><label className="late-session-rule-toggle"><input type="checkbox" checked={draft.intraday_average_enabled} onChange={(event) => onChange({ intraday_average_enabled: event.target.checked })} /><b>分时黄线关系</b></label><select value={draft.intraday_relation} disabled={!draft.intraday_average_enabled} onChange={(event) => onChange({ intraday_relation: event.target.value as LateSessionRuleSettings["intraday_relation"] })}><option value="above">最新价高于黄线</option><option value="below">最新价低于黄线</option><option value="any">不限制方向</option></select></div>
    </div>
  </section>;
}

export function LateSessionSelectionView({ load, analyze = loadLateSessionAIAnalysis }: { load: LateSessionSelectionLoader; analyze?: (selection: LateSessionSelectionResponse) => Promise<LateSessionAIAnalysis> }) {
  const [snapshot, setSnapshot] = useState<LateSessionSelectionResponse | null>(null);
  const [activeSettings, setActiveSettings] = useState<LateSessionRuleSettings | undefined>();
  const [draft, setDraft] = useState<LateSessionRuleSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadProgress, setLoadProgress] = useState<LoadProgress | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<LateSessionAIAnalysis | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [streamState, setStreamState] = useState<RealtimeStreamState | "idle">("idle");
  const streamConnected = useRef(false);
  const settingsRef = useRef(activeSettings);
  settingsRef.current = activeSettings;

  useEffect(() => {
    const controller = new AbortController();
    void consumeRealtimeStream<LateSessionSelectionResponse>(
      ["late_session_candidates"],
      (event) => {
        const incoming = event.payload;
        if (!incoming?.server_time || !incoming?.settings) return;
        const expected = settingsRef.current;
        if (expected && JSON.stringify(incoming.settings) !== JSON.stringify(expected)) return;
        setSnapshot((current) => {
          if (current && Date.parse(incoming.server_time) < Date.parse(current.server_time)) return current;
          return incoming;
        });
        setError(null);
      },
      controller.signal,
      (state) => { streamConnected.current = state === "connected"; setStreamState(state); },
    ).catch(() => {
      if (!controller.signal.aborted) { streamConnected.current = false; setStreamState("error"); }
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    const refresh = async (foreground: boolean) => {
      if (foreground) { setLoading(true); setLoadProgress(null); }
      try {
        const next = await load(activeSettings, foreground ? setLoadProgress : undefined);
        if (!disposed) {
          setSnapshot(next);
          setError(null);
          if (!activeSettings) { setActiveSettings(next.settings); setDraft(next.settings); }
          const interval = streamConnected.current ? Math.max(30_000, next.next_refresh_ms) : Math.max(1000, next.next_refresh_ms);
          timer = window.setTimeout(() => void refresh(false), interval);
        }
      } catch (cause) {
        if (!disposed) { setError(cause instanceof Error ? cause.message : "尾盘选股数据加载失败"); timer = window.setTimeout(() => void refresh(false), 5000); }
      } finally {
        if (!disposed) { setApplying(false); if (foreground) setLoading(false); }
      }
    };
    void refresh(true);
    return () => { disposed = true; if (timer) window.clearTimeout(timer); };
  }, [load, activeSettings]);

  const aiKey = useMemo(() => snapshot ? [snapshot.trading_date, snapshot.candidate_count, snapshot.no_data_reason ?? "", snapshot.candidates.map((item) => item.quote.symbol).join(",")].join("|") : "", [snapshot]);
  useEffect(() => {
    if (!snapshot) return;
    let disposed = false;
    setAiLoading(true);
    setAiError(null);
    void analyze(snapshot).then((result) => { if (!disposed) setAiAnalysis(result); }).catch((cause) => { if (!disposed) setAiError(cause instanceof Error ? cause.message : "尾盘选股 AI 分析失败"); }).finally(() => { if (!disposed) setAiLoading(false); });
    return () => { disposed = true; };
  }, [analyze, aiKey]);

  const updateDraft = (patch: Partial<LateSessionRuleSettings>) => setDraft((current) => current ? { ...current, ...patch } : current);
  const applyRules = () => { if (draft) { setApplying(true); setActiveSettings({ ...draft }); } };
  const resetRules = () => { if (snapshot) { setDraft(snapshot.default_settings); setApplying(true); setActiveSettings({ ...snapshot.default_settings }); } };
  const hasObservationCandidates = snapshot?.candidates.some((candidate) => !candidate.passed) ?? false;

  if (!snapshot) return <main className="late-session-page"><div className="late-session-loading"><RefreshCw className="spin" size={20} /><b>正在读取真实尾盘数据</b><small>等待通达信本地快照，不使用模拟候选</small><DailyRefreshStatus label="尾盘选股" loading progress={loadProgress} /></div></main>;
  return <main className="late-session-page">
    <header className="late-session-hero"><div><p className="eyebrow">A-SHARE / LATE SESSION SCREENER</p><h1>尾盘选股</h1><p>优先展示严格通过项；严格项为空时，保留已通过可验证条件的观察候选。</p></div><div className={`late-session-phase ${snapshot.phase}`}><Clock3 size={18} /><b>{phaseLabel[snapshot.phase]}</b><small>{stageLabel[snapshot.monitor_stage]} · {streamState === "connected" ? "实时推送" : "轮询保底"}</small></div></header>
    {error && <div className="late-session-error"><ShieldAlert size={16} />{error}</div>}
    <DailyRefreshStatus label="尾盘选股" loading={loading} completion={snapshot.data_state === "partial" ? "partial" : "live"} progress={loadProgress} error={error} updatedAt={snapshot.server_time} />
    <section className="late-session-status-strip"><span><Database size={15} />全市场 <b>{snapshot.quote_count}</b> / {snapshot.universe_count} 只</span><span><Activity size={15} />候选 <b>{snapshot.candidate_count}</b> 只</span><span>数据质量 <b>{snapshot.source_quality === "ready" ? "完整" : snapshot.source_quality === "partial" ? "部分可用" : snapshot.source_quality === "stale" ? "缓存" : "不可用"}</b></span><span>状态 <b>{snapshot.status === "ready" ? "已完成" : snapshot.status === "partial" ? "部分字段" : "等待数据"}</b></span></section>
    <section className="late-session-candidates">
      <header><div><p className="eyebrow">{hasObservationCandidates ? "CORE RULE OBSERVATIONS" : "STRICT CANDIDATES"}</p><h2>{hasObservationCandidates ? "核心条件观察候选" : snapshot.phase === "pre_screen" ? "14:30前预筛候选" : "符合当前规则的候选"}</h2></div><small>{hasObservationCandidates ? "时间、涨幅、换手率和市值已通过；其他条件逐股标注" : snapshot.phase === "pre_screen" ? "预筛命中后，实时窗口继续验证时间和尾盘行为" : "候选只保留真实通过项"}</small></header>
      {snapshot.candidates.length === 0
        ? <div className="late-session-empty"><AlertTriangle size={20} /><b>{snapshot.phase === "pre_screen" ? "当前没有符合当前规则的预筛股票" : "当前没有完整通过当前规则的股票"}</b><p>{snapshot.no_data_reason ?? (snapshot.limitations.join("；") || "等待数据或调整筛选规则后再判断。")}</p></div>
        : <div className="late-session-candidate-grid">{snapshot.candidates.map(candidate => <article key={candidate.quote.symbol} data-lifecycle={candidate.lifecycle_status}>
          <header><div><b>{candidate.quote.name}</b><small>{candidate.quote.symbol}</small></div><strong>{candidate.quote.change_percent}%</strong></header>
          <div className="late-session-lifecycle"><b>{lifecycleLabel[candidate.lifecycle_status]}</b><span>持续 {durationLabel(candidate.continuous_seconds)}</span><span>触发 {candidate.trigger_count} 次</span><span>确认 {candidate.continuous_hits} 轮</span></div>
          <div className="late-session-candidate-metrics"><span>价格 <b>{candidate.quote.price}</b></span><span>量比 <b>{candidate.quote.volume_ratio ?? "—"}</b></span><span>换手 <b>{candidate.quote.turnover_rate ?? "—"}%</b></span><span>市值 <b>{candidate.quote.market_cap_yi ?? "—"}亿</b></span></div>
          <div className="late-session-tags">{[...candidate.behavior_tags, ...(!candidate.passed ? candidate.risk_notes : [])].map(tag => <span key={tag}>{tag}</span>)}</div>
          <p className="late-session-change">{candidate.latest_change ?? "候选状态待确认"}</p>
          <footer>{candidate.passed ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}{candidate.passed ? snapshot.phase === "pre_screen" ? "当前规则通过，待尾盘确认" : "当前规则全部通过" : "核心条件通过，其他条件未通过或待补齐"} · {new Date(candidate.quote.observed_at).toLocaleTimeString("zh-CN", { hour12: false })}</footer>
        </article>)}</div>}
      {snapshot.invalidated_candidates.length > 0 && <div className="late-session-invalidated"><b>最近失效</b>{snapshot.invalidated_candidates.map((candidate) => <span key={candidate.quote.symbol}>{candidate.quote.name} {candidate.quote.symbol} · {candidate.invalidation_reason}</span>)}</div>}
    </section>
    <section className="late-session-ai-panel"><header><div><p className="eyebrow">AI / EVIDENCE PARSER</p><h2>筛选结果 AI 分析与解析</h2></div><small>只分析当前真实筛选结果，不补造股票和字段</small></header>{aiLoading ? <div className="late-session-ai-loading" role="status" aria-busy="true"><RefreshCw className="spin" size={17} />正在解析当前筛选结果…</div> : aiError ? <div className="late-session-ai-error"><ShieldAlert size={16} />{aiError}</div> : aiAnalysis ? <div className="late-session-ai-content"><div className={`late-session-ai-badge ${aiAnalysis.status}`}><b>{aiAnalysis.title}</b><span>{aiAnalysis.candidate_count} 只候选</span></div><p className="late-session-ai-summary">{aiAnalysis.summary}</p>{aiAnalysis.reason && <p className="late-session-ai-reason"><b>原因：</b>{aiAnalysis.reason}</p>}<div className="late-session-ai-columns"><div><b>重点解析</b>{aiAnalysis.key_points.map((item) => <span key={item}>• {item}</span>)}</div><div><b>风险与数据边界</b>{[...aiAnalysis.risk_points, ...aiAnalysis.data_gaps].map((item) => <span key={item}>• {item}</span>)}</div></div></div> : <div className="late-session-ai-loading">等待筛选结果解析</div>}</section>
    <section className="late-session-behaviors"><header><div><p className="eyebrow">BEHAVIOR GUIDE</p><h2>六类尾盘行为</h2></div><small>仅作观察与风险提示，不构成买卖建议</small></header><div className="late-session-behavior-grid">{snapshot.behaviors.map(item => <article key={item.key} data-level={item.level}><header><b>{item.title}</b><span>{item.level === "risk" ? "风险提示" : item.level === "observe" ? "观察" : "待核验"}</span></header><p>{item.description}</p><small>{item.evidence.join("；")}</small></article>)}</div></section>
    <section className="late-session-rule-grid">{snapshot.rules.map(rule => <article key={rule.key} data-status={rule.status}><header><b>{rule.label}</b><span>{statusLabel(rule.status)}</span></header><strong>{rule.actual ?? "—"}</strong><small>目标：{rule.target}</small><p>{rule.detail}</p></article>)}</section>
    {draft && <RuleEditor draft={draft} defaultSettings={snapshot.default_settings} onChange={updateDraft} onApply={applyRules} onReset={resetRules} applying={applying} />}
    {snapshot.limitations.length > 0 && <footer className="late-session-limitations"><AlertTriangle size={15} /><span>{snapshot.limitations.join("；")}</span></footer>}
  </main>;
}
