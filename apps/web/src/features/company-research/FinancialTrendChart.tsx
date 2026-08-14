import type { EChartsOption } from "echarts";

import { QuantChart } from "../quant-analysis/QuantChart";
import { chartTheme } from "../../shared/visualization/chartTheme";
import type { FinancialPeriod } from "./types";


function value(raw: string | null): number | null {
  if (raw === null || raw === "") return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

export function financialTrendOption(periods: FinancialPeriod[]): EChartsOption {
  const rows = periods.slice(-8);
  const axis = rows.map((item) => item.period.slice(0, 7));
  return {
    animation: false,
    tooltip: { trigger: "axis", backgroundColor: chartTheme.tooltipBackgroundColor, borderColor: chartTheme.liveColor, textStyle: { color: chartTheme.textColor } },
    legend: { top: 0, right: 8, textStyle: { color: chartTheme.mutedTextColor }, data: ["营收", "净利润", "经营现金流"] },
    grid: { left: 62, right: 24, top: 34, bottom: 34 },
    xAxis: { type: "category", data: axis, axisLine: { lineStyle: { color: chartTheme.gridColor } }, axisLabel: { color: chartTheme.mutedTextColor } },
    yAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: chartTheme.gridColor } }, axisLabel: { color: chartTheme.mutedTextColor } },
    series: [
      { name: "营收", type: "bar", data: rows.map((item) => value(item.revenue)), itemStyle: { color: chartTheme.liveColor }, barMaxWidth: 24 },
      { name: "净利润", type: "line", data: rows.map((item) => value(item.net_profit)), connectNulls: false, symbolSize: 6, lineStyle: { color: chartTheme.upColor, width: 2 }, itemStyle: { color: chartTheme.upColor } },
      { name: "经营现金流", type: "line", data: rows.map((item) => value(item.operating_cash_flow)), connectNulls: false, symbolSize: 5, lineStyle: { color: chartTheme.warningColor, width: 1.5 }, itemStyle: { color: chartTheme.warningColor } },
    ],
  };
}

export function FinancialTrendChart({ periods }: { periods: FinancialPeriod[] }) {
  if (!periods.length) return <p className="financial-note">多年财务序列暂不可用，不以估算值填补。</p>;
  return <div className="research-financial-trend-chart"><QuantChart option={financialTrendOption(periods)} ariaLabel="营收净利润与经营现金流趋势" /></div>;
}
