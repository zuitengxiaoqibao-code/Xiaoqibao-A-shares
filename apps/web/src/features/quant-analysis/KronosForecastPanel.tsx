import type { EChartsOption } from "echarts";
import { AlertTriangle, Cpu, Database, ShieldAlert } from "lucide-react";

import { QuantChart } from "./QuantChart";
import type { KronosForecastResponse } from "./types";

type Props = {
  forecast: KronosForecastResponse | null;
  loading: boolean;
  error: string;
};

const gridColor = "rgba(74, 105, 135, .22)";
const axisColor = "#63758a";
const gold = "#f4c76a";
const cyan = "#34d6ff";
const magenta = "#ff5c8a";

function number(value: string | null | undefined): number | null {
  if (!value) return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

function formatPercent(value: string | null | undefined): string {
  const result = number(value);
  if (result === null) return "--";
  return `${result >= 0 ? "+" : ""}${result.toFixed(2)}%`;
}

function reasonText(reason: string): string {
  return {
    kronos_disabled: "模型未启用：需要在本地设置中开启 Kronos。",
    kronos_repo_not_configured: "未配置 Kronos 源码目录。",
    kronos_dependencies_missing: "缺少 PyTorch 或 Kronos 运行依赖。",
    kronos_model_unavailable: "模型权重不可用或尚未下载。",
    daily_history_insufficient: "日线历史长度不足，暂不生成预测。",
    future_trading_dates_insufficient: "无法确认足够的未来交易日。",
    kronos_runtime_error: "Kronos 运行时返回错误，其他证据面板不受影响。",
  }[reason] ?? reason;
}

function chartOption(forecast: KronosForecastResponse): EChartsOption {
  const points = forecast.points;
  return {
    animation: false,
    textStyle: { color: "#aab9ca", fontFamily: "JetBrains Mono, Consolas, monospace" },
    grid: { left: 54, right: 24, top: 28, bottom: 38 },
    tooltip: { trigger: "axis", backgroundColor: "#071018", borderColor: gold, textStyle: { color: "#d8e6f1" } },
    legend: { top: 0, right: 6, textStyle: { color: axisColor }, data: ["中位路径", "下界", "上界"] },
    xAxis: { type: "category", data: points.map((point) => point.trade_date), axisLine: { lineStyle: { color: gridColor } }, axisLabel: { color: axisColor, hideOverlap: true } },
    yAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: gridColor } }, axisLabel: { color: axisColor } },
    series: [
      { name: "中位路径", type: "line", data: points.map((point) => number(point.median_close)), symbol: "none", lineStyle: { color: gold, width: 2 }, areaStyle: { color: "rgba(244,199,106,.08)" } },
      { name: "下界", type: "line", data: points.map((point) => number(point.lower_close)), symbol: "none", lineStyle: { color: magenta, width: 1, type: "dashed" } },
      { name: "上界", type: "line", data: points.map((point) => number(point.upper_close)), symbol: "none", lineStyle: { color: cyan, width: 1, type: "dashed" } },
    ],
  };
}

function StatusBody({ forecast }: { forecast: KronosForecastResponse }) {
  if (forecast.status === "ready" && forecast.summary && forecast.points.length > 0) {
    return <>
      <QuantChart option={chartOption(forecast)} ariaLabel="Kronos 价格路径预测" />
      <div className="kronos-summary-grid">
        <span><small>预测中位收益</small><b>{formatPercent(forecast.summary.median_return_pct)}</b></span>
        <span><small>预测区间</small><b>{formatPercent(forecast.summary.lower_return_pct)} / {formatPercent(forecast.summary.upper_return_pct)}</b></span>
        <span><small>下行概率</small><b>{number(forecast.summary.downside_probability_pct)?.toFixed(2) ?? "--"}%</b></span>
        <span><small>路径分歧度</small><b>{number(forecast.summary.path_dispersion_pct)?.toFixed(2) ?? "--"}%</b></span>
      </div>
      <p className="quant-panel-note">{forecast.sample_count} 条随机路径的摘要，仅用于观察价格情景，不是交易概率或买卖价格。</p>
    </>;
  }
  const icon = forecast.status === "insufficient" ? <Database size={24} /> : forecast.status === "error" ? <ShieldAlert size={24} /> : <Cpu size={24} />;
  const title = forecast.status === "insufficient" ? "历史日线不足" : forecast.status === "error" ? "预测服务暂不可用" : "Kronos 模型未启用";
  return <div className="quant-empty kronos-empty">{icon}<b>{title}</b>{forecast.reasons.map((reason) => <p key={reason}>{reasonText(reason)}</p>)}<small>模型状态不会影响规则、情绪和回测证据。</small></div>;
}

export function KronosForecastPanel({ forecast, loading, error }: Props) {
  return <section className="quant-panel kronos-forecast-panel" role="region" aria-label="Kronos 价格路径预测">
    <header><div><span>Q5 / PRICE PATH</span><h2>Kronos 价格路径预测</h2></div><Cpu size={18} /></header>
    {loading && <div className="quant-empty" aria-busy="true"><span className="scanner" /><b>正在读取价格路径模型</b><p>只加载已验证日线，不会生成临时曲线。</p></div>}
    {!loading && error && <div className="quant-empty"><AlertTriangle size={24} /><b>{error}</b><p>请稍后重试，其他分析证据仍然有效。</p></div>}
    {!loading && !error && forecast && <StatusBody forecast={forecast} />}
    {!loading && !error && !forecast && <div className="quant-empty"><Cpu size={24} /><b>等待预测状态</b><p>选择标的后读取可用模型证据。</p></div>}
  </section>;
}
