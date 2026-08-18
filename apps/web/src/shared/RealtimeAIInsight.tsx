import { BrainCircuit, ShieldAlert } from "lucide-react";

export type RealtimeAIInsightPayload = {
  kind: string;
  reason: string;
  status: "ready" | "unavailable";
  explanation: string | null;
  statements: Array<{ kind: "fact" | "interpretation"; text: string; evidence_ids?: string[] }>;
  generated_at: string;
  source: string;
  input_snapshot_hash: string;
  coverage_percent: number | null;
  fallback: boolean;
  missing_fields: string[];
};

type Props = {
  insight: RealtimeAIInsightPayload | null;
  domainLabel: string;
};

export function RealtimeAIInsight({ insight, domainLabel }: Props) {
  return <section className="realtime-ai-insight quant-panel" aria-label={`${domainLabel}实时 AI 分析`}>
    <header><div><span>EVENT-TRIGGERED / AI EVIDENCE</span><h2>实时 AI 研判</h2></div><BrainCircuit size={18} /></header>
    {!insight ? <div className="quant-empty"><BrainCircuit size={22} /><b>等待有效变化触发分析</b><p>只有市场风格、风险阈值、候选状态、研究版本或已核验新闻发生变化时才会触发，不会重复消耗模型。</p></div> : <div className="realtime-ai-body">
      <div className="realtime-ai-meta"><span className={insight.status === "ready" ? "up" : "muted"}>{insight.status === "ready" ? "AI 已完成" : "规则解释回退"}</span><span>{insight.reason}</span><span>{new Date(insight.generated_at).toLocaleString("zh-CN", { hour12: false })}</span></div>
      <p className="realtime-ai-summary">{insight.explanation ?? "AI 未配置或暂不可用；以下仅保留基于真实快照的规则解释。"}</p>
      <div className="realtime-ai-statements">{insight.statements.slice(0, 4).map((item, index) => <article key={`${item.kind}-${index}`}><b>{item.kind === "fact" ? "事实" : "解释"}</b><span>{item.text}</span></article>)}</div>
      <div className="realtime-ai-evidence"><span>输入哈希 {insight.input_snapshot_hash.slice(0, 16)}…</span><span>来源 {insight.source}</span><span>覆盖 {insight.coverage_percent == null ? "--" : `${insight.coverage_percent}%`}</span>{insight.missing_fields.length > 0 && <span><ShieldAlert size={13} />缺失 {insight.missing_fields.join("、")}</span>}</div>
    </div>}
  </section>;
}
