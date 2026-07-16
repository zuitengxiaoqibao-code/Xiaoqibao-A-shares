import { AlertTriangle, CalendarDays, Clock3, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { BacktestPanel } from "../backtest/BacktestPanel";
import type { BacktestResult } from "../backtest/types";
import type { Advice, DecisionPhase, DecisionResponse } from "../decision-workbench/types";
import { phaseExecutionCopy } from "../decision-workbench/phaseExecution";
import { friendlyError } from "../../shared/friendlyError";

const phaseNames: Record<DecisionPhase, string> = { premarket: "盘前研判", intraday: "盘中观察", postclose: "盘后复盘" };
const actionNames: Record<Advice["action"], string> = { observe: "加入观察", wait: "暂不参与", avoid: "回避", invalidated: "已失效" };
const outcomeStatusNames: Record<string, string> = { correct: "判断成立", unverifiable: "无法验证", wrong: "判断未成立", invalidated: "条件失效", risk_blocked: "风险拦截" };
const outcomeAttributionNames: Record<string, string> = { trend_failure: "趋势结果", data_unavailable: "数据不足", risk_event: "风险事件", news_misread: "新闻解读", data_issue: "数据问题", rule_block: "规则拦截" };

function postcloseOutcome(item: Advice, phase: DecisionPhase) {
  if (phase !== "postclose") return null;
  const statusCode = item.quantitative_result.outcome_status;
  if (!statusCode || !outcomeStatusNames[statusCode]) return null;
  const attributionCode = item.quantitative_result.error_attribution;
  return { status: outcomeStatusNames[statusCode], attribution: attributionCode ? outcomeAttributionNames[attributionCode] : null };
}

export function HistoryReview({ loadCurrent, loadDate, symbol, runBacktest }: { loadCurrent: () => Promise<DecisionResponse>; loadDate?: (date: string) => Promise<DecisionResponse>; symbol: string | null; runBacktest?: (symbol: string, signal?: AbortSignal) => Promise<BacktestResult> }) {
  const [data, setData] = useState<DecisionResponse | null>(null); const [error, setError] = useState(""); const [date, setDate] = useState(""); const request = useRef(0);
  const load = useCallback(async (selected?: string) => { const current = ++request.current; setError(""); try { const next = selected && loadDate ? await loadDate(selected) : await loadCurrent(); if (current === request.current) { setData(next); setDate(next.trading_date); } } catch (reason) { if (current === request.current) setError(friendlyError(reason, "历史复盘")); } }, [loadCurrent, loadDate]);
  useEffect(() => { void load(); return () => { request.current += 1; }; }, [load]);
  return <main className="beginner-page history-review"><header><p className="eyebrow">历史复盘</p><h1>按日期查看判断变化</h1><p>只展示当时可见的结论、证据和风险。</p><label><CalendarDays size={16} />复盘日期<input aria-label="复盘日期" type="date" value={date} onChange={(event) => { setDate(event.target.value); void load(event.target.value); }} /></label></header>
    {error && <section className="beginner-empty" role="alert"><AlertTriangle /><h2>{error}</h2><button onClick={() => void load(date || undefined)}>重试</button></section>}
    {data && <><p className="history-date">{data.trading_date}{symbol ? ` · ${symbol}` : " · 尚未选择 A 股"}</p><div className="history-phases">{(["premarket", "intraday", "postclose"] as DecisionPhase[]).map((phase) => { const slot = data.phases[phase]; const items = slot.advice.filter((item) => !symbol || item.symbol === symbol); const item = items.at(-1); const executionCopy = phaseExecutionCopy(slot.execution, phase); const phaseRan = slot.phase_status !== "empty" || slot.aggregate_version !== null || slot.execution?.status === "completed"; const emptyMessage = executionCopy?.label ?? (phaseRan ? (symbol ? "本阶段已运行，当时未纳入这只股票" : "本阶段已运行，没有可展示的 A 股") : "本阶段没有生成可核验记录"); const outcome = item ? postcloseOutcome(item, phase) : null; return <section key={phase}><h2>{phaseNames[phase]}</h2>{!item ? <p>{emptyMessage}</p> : <><span>{actionNames[item.action]}</span><h3>{item.conclusion}</h3>{outcome && <div className="history-outcome"><strong>复盘结果：{outcome.status}</strong>{outcome.attribution && <p>归因：<span>{outcome.attribution}</span></p>}</div>}<p>{item.plain_language_explanation}</p>{item.supporting_evidence.slice(0, 3).map((evidence) => <p key={evidence.evidence_id}>{evidence.summary}</p>)}{item.risks.slice(0, 3).map((risk) => <p className="history-risk" key={risk}><ShieldAlert size={14} />{risk}</p>)}<time><Clock3 size={13} />{new Date(item.created_at).toLocaleString("zh-CN", { hour12: false })}</time></>}</section>; })}</div></>}
    {runBacktest && <BacktestPanel symbol={symbol ?? ""} runBacktest={runBacktest} />}
  </main>;
}
