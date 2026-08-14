import { Filter, ShieldAlert } from "lucide-react";

import type { CandidateSelectionFunnel } from "./types";
import { blockerLabel } from "../../shared/evidence/freshnessCopy";

const exclusionLabels: Record<string, string> = {
  insufficient_history: "日线历史不足",
  invalid_history: "历史数据异常",
  stale_history: "历史未到确认交易日",
  insufficient_liquidity: "流动性未达标",
  trigger_not_confirmed: "盘中触发未确认",
  risk_flags: "存在风险标记",
};


export function CandidateFunnel({ funnel }: { funnel: CandidateSelectionFunnel }) {
  const universe = funnel.stages[0]?.count ?? 0;
  const exclusions = Object.entries(funnel.exclusion_reasons)
    .filter(([, count]) => count > 0)
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
  return <section className="candidate-funnel" role="region" aria-label="候选筛选漏斗">
    <header>
      <div><Filter size={15} /><h3>候选筛选漏斗</h3></div>
      <span className={`funnel-quality ${funnel.completeness}`}>{funnel.completeness === "complete" ? "数据完整" : funnel.completeness === "partial" ? "部分完整" : "不可判定"}</span>
    </header>
    <div className="candidate-funnel-stages">
      {funnel.stages.map((stage, index) => {
        const previous = index === 0 ? universe : funnel.stages[index - 1]?.count ?? 0;
        const retained = previous > 0 ? Math.min(100, stage.count / previous * 100) : 0;
        return <article data-stage={stage.key} key={stage.key}>
          <span>{stage.label}</span>
          <strong>{stage.count.toLocaleString("zh-CN")}</strong>
          <i><b style={{ width: `${retained}%` }} /></i>
          <small>{index === 0 ? "本地全市场样本" : `本阶段保留 ${retained.toFixed(1)}%`}</small>
        </article>;
      })}
    </div>
    {(funnel.blockers.length > 0 || exclusions.length > 0) && <footer>
      <div className="funnel-blockers">
        {funnel.blockers.map((item) => <span key={item}><ShieldAlert size={13} />{blockerLabel(item)}</span>)}
      </div>
      <div className="funnel-exclusions">
        {exclusions.map(([reason, count]) => <span key={reason}>{exclusionLabels[reason] ?? reason} <b>{count.toLocaleString("zh-CN")} 只</b></span>)}
      </div>
    </footer>}
  </section>;
}
