import { BarChart3, Building2, Microscope, Radar, X } from "lucide-react";
import type { ReactNode } from "react";

import type { MetricContract } from "../../../shared/evidence/metricContract";
import { ScreenerWorkbench } from "../../../shared/screener/ScreenerWorkbench";

export type DrilldownStock = {
  symbol: string;
  name: string;
  reason: string;
  value?: ReactNode;
};

export type MetricDrilldownSelection = {
  label: string;
  value: string | number;
  source: string;
  stocks?: DrilldownStock[];
  unavailableReason?: string;
  totalLabel?: string;
  contract?: MetricContract;
};

export type StockResearchActions = {
  onOpenAShare?: (symbol: string) => void;
  onOpenCompanyResearch?: (symbol: string) => void;
  onOpenQuantAnalysis?: (symbol: string) => void;
};

export function DrilldownMetric({ item, selected, onSelect, children, ariaLabelPrefix }: {
  item: MetricDrilldownSelection;
  selected: boolean;
  onSelect: (item: MetricDrilldownSelection) => void;
  children: ReactNode;
  ariaLabelPrefix?: string;
}) {
  const action = item.stocks ? "筛选" : "查看口径";
  return <button
    type="button"
    className="metric-drilldown-trigger"
    aria-label={`${ariaLabelPrefix ?? action}：${item.label} ${item.value}`}
    aria-pressed={selected}
    onClick={() => onSelect(item)}
  >{children}<span className="metric-drilldown-hint"><BarChart3 size={13} />{item.stocks ? "查看明细" : "查看口径"}</span></button>;
}

export function MetricDrilldownPanel({ selection, onClose, actions }: {
  selection: MetricDrilldownSelection;
  onClose: () => void;
  actions: StockResearchActions;
}) {
  const stocks = selection.stocks ?? [];
  const contract = selection.contract;
  return <section className="metric-drilldown-panel" role="region" aria-label={`${selection.label} 明细`}>
    <header>
      <div><small>FILTER / EVIDENCE</small><h4>{selection.label} 明细</h4><p>{selection.source} · 统计值 {selection.value}</p></div>
      <button type="button" aria-label={`关闭 ${selection.label} 明细`} onClick={onClose}><X size={17} /></button>
    </header>
    {contract && <dl className="metric-drilldown-contract">
      <div><dt>统计口径</dt><dd>{contract.scope}</dd></div>
      <div><dt>交易日</dt><dd>{contract.tradeDate ?? "未提供"}</dd></div>
      <div><dt>观测时间</dt><dd>{contract.observedAt ? new Date(contract.observedAt).toLocaleString("zh-CN", { hour12: false }) : "未提供"}</dd></div>
      <div><dt>数据来源</dt><dd>{contract.source}</dd></div>
      <div><dt>公式版本</dt><dd>{contract.formulaVersion ?? "原始字段/无公式"}</dd></div>
      <div><dt>样本量</dt><dd>{contract.sampleCount ?? "未提供"}</dd></div>
    </dl>}
    {(selection.stocks || contract) && <p className="metric-drilldown-scope">
      <span>{selection.totalLabel ?? "当前统计"} {contract?.totalCount ?? selection.value}</span>
      <span>当前已加载可钻取明细 {contract?.loadedMemberCount ?? stocks.length}</span>
    </p>}
    {selection.unavailableReason
      ? <div className="metric-drilldown-unavailable"><BarChart3 size={22} /><b>当前只有聚合统计</b><p>{selection.unavailableReason}</p></div>
      : stocks.length > 0
        ? <ScreenerWorkbench rows={stocks}>{(filteredStocks) => <div className="metric-drilldown-stocks">{filteredStocks.map((stock) => <article key={`${selection.label}-${stock.symbol}`}>
          <div><b>{stock.name}</b><code>{stock.symbol}</code><p>{stock.reason}</p></div>
          {stock.value !== undefined && <strong>{stock.value}</strong>}
          <nav aria-label={`${stock.symbol} ${stock.name} 研究入口`}>
            {actions.onOpenAShare && <button type="button" aria-label={`个股观察：${stock.symbol} ${stock.name}`} onClick={() => actions.onOpenAShare?.(stock.symbol)}><Radar size={14} />个股观察</button>}
            {actions.onOpenCompanyResearch && <button type="button" aria-label={`公司研究：${stock.symbol} ${stock.name}`} onClick={() => actions.onOpenCompanyResearch?.(stock.symbol)}><Building2 size={14} />公司研究</button>}
            {actions.onOpenQuantAnalysis && <button type="button" aria-label={`量化分析：${stock.symbol} ${stock.name}`} onClick={() => actions.onOpenQuantAnalysis?.(stock.symbol)}><Microscope size={14} />量化分析</button>}
          </nav>
        </article>)}</div>}</ScreenerWorkbench>
        : <div className="metric-drilldown-unavailable"><BarChart3 size={22} /><b>当前筛选结果为空</b><p>统计口径可用，但本次快照没有对应记录。</p></div>}
  </section>;
}
