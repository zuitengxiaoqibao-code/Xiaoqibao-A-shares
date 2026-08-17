import { Activity, AlertTriangle, CheckCircle2, Clock3, Database, RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import type { LateSessionSelectionLoader, LateSessionSelectionResponse } from "./types";
import "./lateSessionSelection.css";

const phaseLabel = { pre_screen: "14:30前预筛", live_monitor: "14:30–15:00实时监控", post_close: "15:00收盘冻结" } as const;

function statusLabel(status: string) {
  return status === "passed" ? "通过" : status === "failed" ? "未通过" : "不可用";
}

export function LateSessionSelectionView({ load }: { load: LateSessionSelectionLoader }) {
  const [snapshot, setSnapshot] = useState<LateSessionSelectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    const refresh = async () => {
      try {
        const next = await load();
        if (!disposed) { setSnapshot(next); setError(null); timer = window.setTimeout(refresh, Math.max(1000, next.next_refresh_ms)); }
      } catch (cause) {
        if (!disposed) { setError(cause instanceof Error ? cause.message : "尾盘选股数据加载失败"); timer = window.setTimeout(refresh, 5000); }
      }
    };
    void refresh();
    return () => { disposed = true; if (timer) window.clearTimeout(timer); };
  }, [load]);

  if (!snapshot) return <main className="late-session-page"><div className="late-session-loading"><RefreshCw className="spin" size={20} /><b>正在读取真实尾盘数据</b><small>等待通达信本地快照，不使用模拟候选</small></div></main>;
  return <main className="late-session-page">
    <header className="late-session-hero"><div><p className="eyebrow">A-SHARE / LATE SESSION SCREENER</p><h1>尾盘选股</h1><p>严格按截图七项规则筛选；未满足或缺字段的股票不会进入候选池。</p></div><div className={`late-session-phase ${snapshot.phase}`}><Clock3 size={18} /><b>{phaseLabel[snapshot.phase]}</b><small>{new Date(snapshot.server_time).toLocaleTimeString("zh-CN", { hour12: false })} · 刷新 {snapshot.refresh_interval_ms}ms</small></div></header>
    {error && <div className="late-session-error"><ShieldAlert size={16} />{error}</div>}
    <section className="late-session-status-strip"><span><Database size={15} />全市场 <b>{snapshot.quote_count}</b> / {snapshot.universe_count} 只</span><span><Activity size={15} />候选 <b>{snapshot.candidate_count}</b> 只</span><span>数据质量 <b>{snapshot.source_quality === "ready" ? "完整" : snapshot.source_quality === "partial" ? "部分可用" : "不可用"}</b></span><span>状态 <b>{snapshot.status === "ready" ? "已完成" : snapshot.status === "partial" ? "部分字段" : "等待数据"}</b></span></section>
    <section className="late-session-rule-grid">{snapshot.rules.map(rule => <article key={rule.key} data-status={rule.status}><header><b>{rule.label}</b><span>{statusLabel(rule.status)}</span></header><strong>{rule.actual ?? "—"}</strong><small>目标：{rule.target}</small><p>{rule.detail}</p></article>)}</section>
    <section className="late-session-candidates"><header><div><p className="eyebrow">STRICT CANDIDATES</p><h2>{snapshot.phase === "pre_screen" ? "14:30前预筛候选" : "符合全部规则的候选"}</h2></div><small>{snapshot.phase === "pre_screen" ? "预筛命中后，14:30起继续验证时间闸门和尾盘行为" : "候选只保留真实通过项"}</small></header>{snapshot.candidates.length === 0 ? <div className="late-session-empty"><AlertTriangle size={20} /><b>{snapshot.phase === "pre_screen" ? "当前没有六项条件预筛命中的股票" : "当前没有完整通过七项规则的股票"}</b><p>{snapshot.limitations.join("；") || "等待14:30尾盘窗口或补齐字段后再判断。"}</p></div> : <div className="late-session-candidate-grid">{snapshot.candidates.map(candidate => <article key={candidate.quote.symbol}><header><div><b>{candidate.quote.name}</b><small>{candidate.quote.symbol}</small></div><strong>{candidate.quote.change_percent}%</strong></header><div className="late-session-candidate-metrics"><span>价格 <b>{candidate.quote.price}</b></span><span>量比 <b>{candidate.quote.volume_ratio ?? "—"}</b></span><span>换手 <b>{candidate.quote.turnover_rate ? `${candidate.quote.turnover_rate}%` : "—"}</b></span><span>市值 <b>{candidate.quote.market_cap_yi ? `${candidate.quote.market_cap_yi}亿` : "—"}</b></span></div><div className="late-session-tags">{candidate.behavior_tags.map(tag => <span key={tag}>{tag}</span>)}</div><footer><CheckCircle2 size={14} />{snapshot.phase === "pre_screen" ? "六项条件通过，待尾盘确认" : "七项规则全部通过"} · {new Date(candidate.quote.observed_at).toLocaleTimeString("zh-CN", { hour12: false })}</footer></article>)}</div>}</section>
    <section className="late-session-behaviors"><header><div><p className="eyebrow">BEHAVIOR GUIDE</p><h2>六类尾盘行为</h2></div><small>仅作观察与风险提示，不构成买卖建议</small></header><div className="late-session-behavior-grid">{snapshot.behaviors.map(item => <article key={item.key} data-level={item.level}><header><b>{item.title}</b><span>{item.level === "risk" ? "风险提示" : item.level === "observe" ? "观察" : "待核验"}</span></header><p>{item.description}</p><small>{item.evidence.join("；")}</small></article>)}</div></section>
    {snapshot.limitations.length > 0 && <footer className="late-session-limitations"><AlertTriangle size={15} /><span>{snapshot.limitations.join("；")}</span></footer>}
  </main>;
}
