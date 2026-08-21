import { AlertTriangle, CalendarDays, Clock3, Database, RotateCcw, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { BacktestPanel } from "../backtest/BacktestPanel";
import type { BacktestRunner } from "../backtest/types";
import type { Advice, DecisionPhase, DecisionResponse } from "../decision-workbench/types";
import { beginnerAdviceExplanation } from "../decision-workbench/explanation";
import { phaseExecutionCopy } from "../decision-workbench/phaseExecution";
import { friendlyError } from "../../shared/friendlyError";
import { loadWorkspaceState, saveWorkspaceState } from "../../shared/workspace/workspaceState";
import { apiClient } from "../../shared/apiClient";

const phaseNames: Record<DecisionPhase, string> = { premarket: "盘前研判", intraday: "盘中观察", postclose: "盘后复盘" };
const actionNames: Record<Advice["action"], string> = { observe: "加入观察", wait: "暂不参与", avoid: "回避", invalidated: "已失效" };
const outcomeStatusNames: Record<string, string> = { correct: "判断成立", unverifiable: "无法验证", wrong: "判断未成立", invalidated: "条件失效", risk_blocked: "风险拦截" };
const outcomeAttributionNames: Record<string, string> = { trend_failure: "趋势结果", data_unavailable: "数据不足", risk_event: "风险事件", news_misread: "新闻解读", data_issue: "数据问题", rule_block: "规则拦截" };
type FrozenPostclose = { report_id: string; trading_date: string; observed_at: string; quality: string; coverage: string; ai_status: string; delivery: { feishu?: { status: string; reason?: string | null } } };

function postcloseOutcome(item: Advice, phase: DecisionPhase) {
  if (phase !== "postclose") return null;
  const statusCode = item.quantitative_result.outcome_status;
  if (!statusCode || !outcomeStatusNames[statusCode]) return null;
  const attributionCode = item.quantitative_result.error_attribution;
  return { status: outcomeStatusNames[statusCode], attribution: attributionCode ? outcomeAttributionNames[attributionCode] : null };
}

export function HistoryReview({ loadCurrent, loadDate, symbol, runBacktest }: { loadCurrent: () => Promise<DecisionResponse>; loadDate?: (date: string) => Promise<DecisionResponse>; symbol: string | null; runBacktest?: BacktestRunner }) {
  const [restoredDate] = useState(() => loadWorkspaceState()?.asOf ?? null);
  const [data, setData] = useState<DecisionResponse | null>(null); const [error, setError] = useState(""); const [date, setDate] = useState(restoredDate ?? ""); const request = useRef(0);
  const [frozen, setFrozen] = useState<FrozenPostclose | null>(null); const [retrying, setRetrying] = useState(false);
  const load = useCallback(async (selected?: string) => { const current = ++request.current; setError(""); try { const next = selected && loadDate ? await loadDate(selected) : await loadCurrent(); if (current === request.current) { setData(next); setDate(next.trading_date); saveWorkspaceState({ route: "/history", menu: "history", asOf: next.trading_date, symbol }); } } catch (reason) { if (current === request.current) setError(friendlyError(reason, "历史复盘")); } }, [loadCurrent, loadDate, symbol]);
  useEffect(() => { void load(restoredDate ?? undefined); return () => { request.current += 1; }; }, [load, restoredDate]);
  useEffect(() => {
    if (!date) { setFrozen(null); return; }
    let active = true;
    void apiClient.get<FrozenPostclose[]>("/api/v1/operations/postclose-reports?limit=100", { context: "盘后冻结报告" })
      .then((items) => { if (active) setFrozen(items.find((item) => item.trading_date === date) ?? null); })
      .catch(() => { if (active) setFrozen(null); });
    return () => { active = false; };
  }, [date]);
  const retryDelivery = async () => {
    if (!frozen) return;
    setRetrying(true);
    try {
      const result = await apiClient.post<{ status: string }>(`/api/v1/operations/postclose-reports/${encodeURIComponent(frozen.report_id)}/retry`, undefined, { context: "飞书投递重试" });
      setFrozen({ ...frozen, delivery: { ...frozen.delivery, feishu: { status: result.status } } });
    } catch (reason) { setError(friendlyError(reason, "飞书投递重试")); } finally { setRetrying(false); }
  };
  return <main className="beginner-page history-review"><header><p className="eyebrow">历史复盘</p><h1>按日期查看判断变化</h1><p>只展示当时可见的结论、证据和风险。</p><label><CalendarDays size={16} />复盘日期<input aria-label="复盘日期" type="date" value={date} onChange={(event) => { setDate(event.target.value); void load(event.target.value); }} /></label></header>
    {error && <section className="beginner-empty" role="alert"><AlertTriangle /><h2>{error}</h2><button onClick={() => void load(date || undefined)}>重试</button></section>}
    {data && <><p className="history-date">{data.trading_date}{symbol ? ` · ${symbol}` : " · 尚未选择 A 股"}</p>{frozen && <section className="history-frozen-report"><div><Database size={18} /><span><h2>盘后冻结报告</h2><p>{frozen.quality === "ready" ? "数据完整" : "数据部分可用"} · 证据覆盖 {frozen.coverage}% · AI {frozen.ai_status === "ready" ? "已完成" : "未生成"}</p></span></div><div className="history-delivery-state"><strong>{frozen.delivery.feishu?.status === "sent" ? "飞书已送达" : frozen.delivery.feishu?.status === "failed" ? "飞书投递失败" : "飞书未配置"}</strong>{frozen.delivery.feishu?.reason && <small>{frozen.delivery.feishu.reason}</small>}{frozen.delivery.feishu?.status === "failed" && <button type="button" disabled={retrying} onClick={() => void retryDelivery()}><RotateCcw size={14} />{retrying ? "正在重试" : "仅重试投递"}</button>}</div></section>}<div className="history-phases">{(["premarket", "intraday", "postclose"] as DecisionPhase[]).map((phase) => { const slot = data.phases[phase]; const items = slot.advice.filter((item) => !symbol || item.symbol === symbol); const item = items.at(-1); const executionCopy = phaseExecutionCopy(slot.execution, phase); const phaseRan = slot.phase_status !== "empty" || slot.aggregate_version !== null || slot.execution?.status === "completed"; const emptyMessage = executionCopy?.label ?? (phaseRan ? (symbol ? "本阶段已运行，当时未纳入这只股票" : "本阶段已运行，没有可展示的 A 股") : "本阶段没有生成可核验记录"); const outcome = item ? postcloseOutcome(item, phase) : null; return <section key={phase}><h2>{phaseNames[phase]}</h2>{!item ? <p>{emptyMessage}</p> : <><span>{actionNames[item.action]}</span><h3>{item.conclusion}</h3>{outcome && <div className="history-outcome"><strong>复盘结果：{outcome.status}</strong>{outcome.attribution && <p>归因：<span>{outcome.attribution}</span></p>}</div>}<p>{beginnerAdviceExplanation(item, phase)}</p>{item.supporting_evidence.slice(0, 3).map((evidence) => <p key={evidence.evidence_id}>{evidence.summary}</p>)}{item.risks.slice(0, 3).map((risk) => <p className="history-risk" key={risk}><ShieldAlert size={14} />{risk}</p>)}<time><Clock3 size={13} />{new Date(item.created_at).toLocaleString("zh-CN", { hour12: false })}</time></>}</section>; })}</div></>}
    {runBacktest && <BacktestPanel symbol={symbol ?? ""} runBacktest={runBacktest} />}
  </main>;
}
