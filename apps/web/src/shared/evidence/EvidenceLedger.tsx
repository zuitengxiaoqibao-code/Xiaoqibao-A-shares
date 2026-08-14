import { ChevronDown, Database, ShieldAlert } from "lucide-react";

export type EvidenceLedgerEntry = {
  source: string;
  operation: string;
  status: "ready" | "partial" | "stale" | "unavailable" | "error";
  trade_date: string | null;
  observed_at: string | null;
  formula_version: string | null;
  sample_count: number | null;
  limitations: string[];
};

const statusLabels: Record<EvidenceLedgerEntry["status"], string> = {
  ready: "可用",
  partial: "部分可用",
  stale: "待更新",
  unavailable: "不可用",
  error: "错误",
};

function timeLabel(value: string | null): string {
  if (!value) return "无观测时间";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("zh-CN", { hour12: false });
}

export function EvidenceLedger({ entries, defaultOpen = false }: { entries: EvidenceLedgerEntry[]; defaultOpen?: boolean }) {
  return <details className="evidence-ledger" open={defaultOpen} role="region" aria-label="证据账本">
    <summary><span><Database size={15} /><b>证据账本</b><small>{entries.length} 条来源链路</small></span><ChevronDown size={15} /></summary>
    <div>
      {entries.map((entry) => <article data-status={entry.status} key={`${entry.source}:${entry.operation}`}>
        <header><div><b>{entry.operation}</b><span>{entry.source}</span></div><em>{statusLabels[entry.status]}</em></header>
        <dl>
          <div><dt>交易日</dt><dd>{entry.trade_date ?? "--"}</dd></div>
          <div><dt>观测时间</dt><dd>{timeLabel(entry.observed_at)}</dd></div>
          <div><dt>公式版本</dt><dd>{entry.formula_version ?? "--"}</dd></div>
          <div><dt>样本量</dt><dd>{entry.sample_count === null ? "--" : `${entry.sample_count.toLocaleString("zh-CN")} 条样本`}</dd></div>
        </dl>
        {entry.limitations.length > 0 && <footer><ShieldAlert size={13} />{entry.limitations.map((item) => <span key={item}>{item}</span>)}</footer>}
      </article>)}
    </div>
  </details>;
}
