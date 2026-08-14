import type { EChartsOption } from "echarts";

import { QuantChart } from "../../features/quant-analysis/QuantChart";
import { ChartPanel, DataStateNotice, EvidenceBadge } from "./VisualPrimitives";
import { chartTheme } from "./chartTheme";
import type { EvidenceState } from "./types";

function evidenceState({ available, source, observedAt }: Pick<FundFlowZeroAxisProps, "available" | "source" | "observedAt">): EvidenceState {
  return {
    status: available > 0 ? "ready" : "unavailable",
    source,
    observedAt,
    coverage: available > 0 ? 100 : null,
    warnings: available > 0 ? [] : ["没有可验证的流入/流出样本，不能绘制零轴柱。"],
  };
}

export type FundFlowZeroAxisProps = {
  inflow: number;
  outflow: number;
  available: number;
  source: string;
  observedAt: string | null;
};

export function FundFlowZeroAxis({ inflow, outflow, available, source, observedAt }: FundFlowZeroAxisProps) {
  const state = evidenceState({ available, source, observedAt });
  if (state.status !== "ready") {
    return <section className="fund-flow-zero-axis viz-chart-panel" aria-label="候选资金流入流出零轴图">
      <header className="viz-chart-panel-header"><div><h3>资金流零轴</h3><p>流入在零轴上方，流出在零轴下方</p></div><EvidenceBadge status={state.status} /></header>
      <DataStateNotice state={state} title="候选资金流：数据不可用" />
    </section>;
  }
  const option: EChartsOption = {
    animation: false,
    textStyle: { color: chartTheme.textColor, fontFamily: chartTheme.fontFamily },
    grid: { left: 44, right: 18, top: 18, bottom: 30 },
    xAxis: { type: "category", data: ["当前阶段"], axisLine: { lineStyle: { color: chartTheme.gridColor } }, axisLabel: { color: chartTheme.mutedTextColor } },
    yAxis: { type: "value", axisLabel: { color: chartTheme.mutedTextColor }, splitLine: { lineStyle: { color: chartTheme.gridColor } } },
    tooltip: { trigger: "axis", backgroundColor: "#071018", borderColor: chartTheme.liveColor, textStyle: { color: chartTheme.textColor } },
    series: [{
      name: "流入 / 流出", type: "bar", barMaxWidth: 54,
      data: [{ value: inflow, itemStyle: { color: chartTheme.upColor } }, { value: -Math.abs(outflow), itemStyle: { color: chartTheme.downColor } }],
      markLine: { silent: true, symbol: "none", lineStyle: { color: chartTheme.mutedTextColor, type: "dashed" }, data: [{ yAxis: 0 }] },
    }],
  };
  return <ChartPanel title="资金流零轴" subtitle={`流入 ${inflow} · 流出 ${outflow} · ${available} 个有效样本`} state={state} ariaLabel="候选资金流入流出零轴图">
    <div className="fund-flow-zero-axis__chart"><QuantChart option={option} ariaLabel="候选资金流入流出零轴图" /></div>
    <footer className="fund-flow-zero-axis__meta">来源：{source} · 观测时间：{observedAt ? new Date(observedAt).toLocaleString("zh-CN", { hour12: false }) : "时间未知"}</footer>
  </ChartPanel>;
}
