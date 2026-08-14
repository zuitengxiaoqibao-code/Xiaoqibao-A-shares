import { ChevronDown, FileSearch, ShieldAlert } from "lucide-react";

export type FieldEvidenceStatus = "live" | "cached" | "postclose" | "stale" | "missing" | "conflict" | "derived";

export type FieldEvidence = {
  field_path: string;
  value: string | number | boolean | null;
  source: string;
  source_field: string | null;
  status: FieldEvidenceStatus;
  trade_date: string | null;
  observed_at: string | null;
  coverage_percent: string | null;
  derived: boolean;
  formula: string | null;
  evidence_ids: string[];
  limitations: string[];
  alternatives?: Array<{ value: string | number | boolean; source: string; source_field: string | null; observed_at: string }>;
  difference?: string | null;
  selection_reason?: string | null;
  affects_conclusion?: boolean | null;
};

const statusLabels: Record<FieldEvidenceStatus, string> = {
  live: "实时", cached: "缓存", postclose: "盘后", stale: "待更新",
  missing: "缺失", conflict: "冲突", derived: "推算",
};

function timeLabel(value: string | null): string {
  if (!value) return "--";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("zh-CN", { hour12: false });
}

export function FieldEvidenceDetails({ entries, defaultOpen = false }: { entries: FieldEvidence[]; defaultOpen?: boolean }) {
  const counts = entries.reduce<Record<string, number>>((result, entry) => {
    result[entry.status] = (result[entry.status] ?? 0) + 1;
    return result;
  }, {});
  return <details className="field-evidence" open={defaultOpen} role="group" aria-label="关键字段证据">
    <summary>
      <span><FileSearch size={15} /><b>关键字段真实性</b></span>
      <span className="field-evidence-summary">
        {Object.entries(counts).map(([status, count]) => <em data-status={status} key={status}>{count} 项{statusLabels[status as FieldEvidenceStatus]}</em>)}
        <ChevronDown size={15} />
      </span>
    </summary>
    <div className="field-evidence-grid">
      {entries.map((entry) => <article data-status={entry.status} key={entry.field_path}>
        <header><span><b>{entry.field_path}</b><small>{entry.source}</small></span><em>{statusLabels[entry.status]}</em></header>
        <strong>{entry.value === null ? "--" : String(entry.value)}</strong>
        <dl>
          <div><dt>原始字段</dt><dd>{entry.source_field ?? "推算字段"}</dd></div>
          <div><dt>交易日</dt><dd>{entry.trade_date ?? "--"}</dd></div>
          <div><dt>观测时间</dt><dd>{timeLabel(entry.observed_at)}</dd></div>
          <div><dt>覆盖率</dt><dd>{entry.coverage_percent === null ? "--" : `${entry.coverage_percent}%`}</dd></div>
          <div className="wide"><dt>公式</dt><dd>{entry.formula ?? "原始字段，无二次推算"}</dd></div>
        </dl>
        {entry.status === "conflict" && !!entry.alternatives?.length && <section className="field-evidence-conflict" aria-label="来源冲突处理">
          <dl>
            <div className="wide"><dt>备选值</dt><dd>{entry.alternatives.map((item) => <span key={`${item.source}:${item.source_field}:${item.observed_at}`}>{String(item.value)} · {item.source}</span>)}</dd></div>
            <div><dt>差异</dt><dd>{entry.difference ?? "--"}</dd></div>
            <div><dt>结论影响</dt><dd>{entry.affects_conclusion ? "影响当前结论" : "不影响当前结论"}</dd></div>
            <div className="wide"><dt>采用理由</dt><dd>{entry.selection_reason ?? "--"}</dd></div>
          </dl>
        </section>}
        {entry.limitations.length > 0 && <footer><ShieldAlert size={13} />{entry.limitations.map((item) => <span key={item}>{item}</span>)}</footer>}
      </article>)}
    </div>
  </details>;
}
