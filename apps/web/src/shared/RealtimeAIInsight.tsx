import { BrainCircuit, ShieldAlert } from "lucide-react";

export type RealtimeAIInsightPayload = {
  kind: string;
  reason: string;
  status: "ready" | "unavailable";
  ai_state?: "unconfigured" | "configured_unverified" | "connected" | "connection_failed" | "output_invalid" | "timeout" | "rate_limited" | "model_not_found";
  ai_message?: string;
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

const reasonLabels: Record<string, string> = {
  initial_verified_snapshot: "首次完成真实数据核验",
  verified_snapshot_changed: "真实数据发生变化",
  research_version_changed: "研究数据版本已更新",
  market_regime_changed: "市场风格发生变化",
  risk_threshold_crossed: "风险阈值发生变化",
  candidate_status_changed: "候选状态发生变化",
  verified_news_changed: "已核验新闻发生变化",
  late_session_candidate_lifecycle_changed: "尾盘候选状态发生变化",
  late_session_candidate_invalidated: "尾盘候选被重新核验",
  late_session_stage_changed: "尾盘筛选阶段已更新",
};

const fieldLabels: Record<string, string> = {
  symbol: "分析标的",
  as_of: "数据日期",
  status: "数据状态",
  evidence_coverage: "证据覆盖率",
  coverage_percent: "证据覆盖率",
  "regime.regime": "市场风格",
  "regime.risk_score": "风险评分",
  "regime.emotion_score": "情绪评分",
  "market_data.phase": "行情阶段",
  formula_version: "分析规则",
  trading_date: "交易日期",
  monitor_stage: "监控阶段",
  data_state: "数据状态",
  source_quality: "来源质量",
};

const valueLabels: Record<string, string> = {
  ready: "完整可用",
  partial: "部分可用",
  unavailable: "暂不可用",
  waiting: "等待数据",
  live: "实时数据",
  rules: "规则分析",
  tdx: "通达信",
  "tdx-local": "本地通达信",
  tencent: "腾讯行情",
  "tencent-realtime": "腾讯实时行情",
  "eastmoney": "东方财富",
};

const missingFieldLabels: Record<string, string> = {
  industry: "行业信息",
  valuation: "估值数据",
  finance: "财务数据",
  announcement: "公告信息",
  events: "事件信息",
};

function labelForValue(value: string): string {
  return valueLabels[value] ?? value;
}

function formatCoverage(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return "--";
  const percent = value <= 1 ? value * 100 : value;
  return `${Math.round(percent)}%`;
}

function formatRawValue(path: string, raw: string): string {
  let value = raw.trim();
  try {
    const parsed = JSON.parse(value) as unknown;
    value = typeof parsed === "string" ? parsed : JSON.stringify(parsed);
  } catch {
    value = value.replace(/^['"]|['"]$/g, "");
  }
  if (path === "evidence_coverage" || path === "coverage_percent") {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? formatCoverage(numeric) : "--";
  }
  if (path === "status" || path === "source" || path === "quality") return labelForValue(value);
  return value;
}

function readableStatement(text: string): { label: string; value: string } | null {
  const match = text.match(/^([a-zA-Z_][\w.]*)\s*=\s*(.+)$/);
  if (!match) return { label: "分析提示", value: text };
  const path = match[1];
  if (path.includes("snapshot_id") || path.includes("hash") || path.includes("input_snapshot")) return null;
  const shortKey = path.split(".").at(-1) ?? path;
  const label = fieldLabels[path] ?? fieldLabels[shortKey] ?? "数据项";
  return { label, value: formatRawValue(path, match[2]) };
}

function isTechnicalText(text: string): boolean {
  return /Company research evidence|\b(symbol|as_of|status|evidence coverage|snapshot_id)\b\s*=?/i.test(text);
}

function companySummary(insight: RealtimeAIInsightPayload, domainLabel: string, facts: Array<{ label: string; value: string }>): string {
  const find = (label: string) => facts.find((fact) => fact.label === label)?.value;
  const status = find("数据状态") ?? (insight.status === "ready" ? "完整可用" : "部分可用");
  const symbol = find("分析标的");
  const date = find("数据日期");
  const coverage = formatCoverage(insight.coverage_percent);
  const subject = symbol ? `分析标的 ${symbol}` : "当前分析标的";
  const when = date ? `，数据日期 ${date}` : "";
  const coverageText = coverage === "--" ? "覆盖率待确认" : `证据覆盖率 ${coverage}`;
  return `${domainLabel}数据已更新：${subject}${when}，当前状态为${status}，${coverageText}。AI 仅基于已核验数据进行解释，不生成交易指令。`;
}

export function RealtimeAIInsight({ insight, domainLabel }: Props) {
  return <section className="realtime-ai-insight quant-panel" aria-label={`${domainLabel}实时 AI 分析`}>
    <header><div><span>变化触发 · AI 证据分析</span><h2>实时 AI 研判</h2></div><BrainCircuit size={18} /></header>
    {!insight ? <div className="quant-empty"><BrainCircuit size={22} /><b>等待有效变化触发分析</b><p>只有市场风格、风险阈值、候选状态、研究版本或已核验新闻发生变化时才会触发，不会重复消耗模型。</p></div> : <div className="realtime-ai-body">
      {(() => {
        const parsedFacts = insight.statements.map((item) => readableStatement(item.text)).filter((item): item is { label: string; value: string } => item !== null);
        const facts = parsedFacts.some((item) => item.label === "证据覆盖率") || insight.coverage_percent == null
          ? parsedFacts.slice(0, 4)
          : [...parsedFacts.slice(0, 3), { label: "证据覆盖率", value: formatCoverage(insight.coverage_percent) }];
        const rawSummary = insight.explanation ?? insight.ai_message ?? "";
        const summary = isTechnicalText(rawSummary) || !rawSummary.trim() ? companySummary(insight, domainLabel, facts) : rawSummary;
        return <>
          <div className="realtime-ai-meta"><span className={insight.status === "ready" ? "up" : "muted"}>{insight.status === "ready" ? "AI 已完成" : "规则解释回退"}</span><span>{reasonLabels[insight.reason] ?? "真实数据发生变化"}</span><span>{new Date(insight.generated_at).toLocaleString("zh-CN", { hour12: false })}</span></div>
          <p className="realtime-ai-summary">{summary}</p>
          <div className="realtime-ai-statements">{facts.map((item, index) => <article key={`${item.label}-${index}`}><b>{item.label}</b><span>{item.value}</span></article>)}</div>
        </>;
      })()}
      <details className="realtime-ai-evidence" role="group" aria-label="实时 AI 数据依据">
        <summary>查看数据质量与来源</summary>
        <div className="realtime-ai-evidence__details"><span>数据来源：{labelForValue(insight.source)}</span><span>证据覆盖率：{formatCoverage(insight.coverage_percent)}</span><span>生成时间：{new Date(insight.generated_at).toLocaleString("zh-CN", { hour12: false })}</span>{insight.missing_fields.length > 0 && <span><ShieldAlert size={13} />待补充：{insight.missing_fields.map((field) => missingFieldLabels[field] ?? field).join("、")}</span>}</div>
      </details>
    </div>}
  </section>;
}
