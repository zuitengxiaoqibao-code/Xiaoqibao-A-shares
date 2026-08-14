import { AlertTriangle, CheckCircle2, ChevronDown, CircleDashed, ShieldAlert } from "lucide-react";

import type { ResearchDecisionLedgerRow } from "./types";

const statusLabel = {
  ready: "证据可用",
  partial: "证据部分可用",
  unavailable: "证据不可用",
  clear: "当前未触发",
  triggered: "需要复核",
} as const;

function StatusIcon({ status }: { status: ResearchDecisionLedgerRow["status"] }) {
  if (status === "triggered") return <ShieldAlert size={16} />;
  if (status === "ready" || status === "clear") return <CheckCircle2 size={16} />;
  if (status === "partial") return <AlertTriangle size={16} />;
  return <CircleDashed size={16} />;
}

export function ResearchDecisionLedger({ rows }: { rows: ResearchDecisionLedgerRow[] }) {
  if (!rows.length) return null;
  return <section className="research-decision-ledger" aria-label="公司研究决策账本">
    <header><div><p className="eyebrow">DECISION LEDGER</p><h2>公司研究决策账本</h2></div><small>低样本不计算前向 PE · 先看边界再展开事实</small></header>
    <div className="research-decision-rows">{rows.map((row) => <details key={row.key} data-status={row.status}>
      <summary>
        <span className="research-decision-icon"><StatusIcon status={row.status} /></span>
        <span className="research-decision-label">{row.label}</span>
        <span className="research-decision-summary">{row.summary}</span>
        <span className="research-decision-status">{statusLabel[row.status]}</span>
        <ChevronDown className="research-decision-chevron" size={16} />
      </summary>
      <div className="research-decision-detail">
        {row.facts.length > 0 ? <ul>{row.facts.map((fact) => <li key={fact}>{fact}</li>)}</ul> : <p>暂无可核验事实。</p>}
        {row.limitation && <p className="research-decision-limitation">边界：{row.limitation}</p>}
        {row.evidence_ids.length > 0 && <small>证据编号：{row.evidence_ids.join(" · ")}</small>}
      </div>
    </details>)}</div>
  </section>;
}
