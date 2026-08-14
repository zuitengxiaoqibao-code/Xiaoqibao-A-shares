import type { CompanyResearchResponse } from "./types";


function number(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function dimension(value: CompanyResearchResponse, key: string, metric: string): number | null {
  return number(value.dimensions.find((item) => item.key === key)?.metrics[metric]);
}

export function ResearchComparisonMatrix({ peers }: { peers: CompanyResearchResponse[] }) {
  if (peers.length < 2) return null;
  const metrics = [
    { label: "研究分", read: (item: CompanyResearchResponse) => number(item.final_score), format: (value: number) => value.toFixed(1) },
    { label: "证据覆盖", read: (item: CompanyResearchResponse) => number(item.evidence_coverage) === null ? null : number(item.evidence_coverage)! * 100, format: (value: number) => `${value.toFixed(0)}%` },
    { label: "营收3年CAGR", read: (item: CompanyResearchResponse) => number(item.financial_history.revenue_cagr_3y) === null ? null : number(item.financial_history.revenue_cagr_3y)! * 100, format: (value: number) => `${value.toFixed(1)}%` },
    { label: "净利润3年CAGR", read: (item: CompanyResearchResponse) => number(item.financial_history.net_profit_cagr_3y) === null ? null : number(item.financial_history.net_profit_cagr_3y)! * 100, format: (value: number) => `${value.toFixed(1)}%` },
    { label: "ROE", read: (item: CompanyResearchResponse) => dimension(item, "profitability", "roe"), format: (value: number) => `${value.toFixed(1)}%` },
    { label: "风险扣分", read: (item: CompanyResearchResponse) => number(item.risk_penalty), format: (value: number) => value.toFixed(1) },
  ];
  return <section className="research-card research-comparison-matrix" aria-label="同行横向比较">
    <div className="research-card-header"><h2>同行横向证据矩阵</h2><span className="research-status partial">同口径原值 · 不做主观排名</span></div>
    <div className="research-comparison-matrix-grid">
      <div className="research-comparison-corner">公司</div>{metrics.map((metric) => <b key={metric.label}>{metric.label}</b>)}
      {peers.map((peer) => <div className="research-comparison-row" key={peer.symbol}>
        <strong>{peer.name}<small>{peer.symbol}</small></strong>
        {metrics.map((metric) => { const current = metric.read(peer); return <span data-state={current === null ? "unavailable" : "ready"} key={metric.label}><small>{metric.label}</small><b>{current === null ? "--" : metric.format(current)}</b><i><em style={{ width: `${current === null ? 0 : Math.max(0, Math.min(100, metric.label === "风险扣分" ? current * 4 : current))}%` }} /></i></span>; })}
      </div>)}
    </div>
  </section>;
}
