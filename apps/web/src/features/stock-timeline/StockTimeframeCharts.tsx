import { Activity, BarChart3 } from "lucide-react";
import type { EChartsOption } from "echarts";

import { QuantChart } from "../quant-analysis/QuantChart";
import { chartTheme } from "../../shared/visualization/chartTheme";
import type { StockTimelineBar, StockTimelineMinutePoint, StockTimelineResponse } from "./types";


const MAJOR_TIMES = new Set(["09:30", "10:00", "10:30", "11:00", "11:30", "13:00", "13:30", "14:00", "14:30", "15:00"]);

function tradingSessionLabels(): string[] {
  const labels: string[] = [];
  const append = (start: number, end: number) => {
    for (let value = start; value <= end; value += 1) {
      labels.push(`${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`);
    }
  };
  append(9 * 60 + 30, 11 * 60 + 30);
  append(13 * 60, 15 * 60);
  return labels;
}

const SESSION_LABELS = tradingSessionLabels();

function minuteLabel(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Shanghai",
  }).format(new Date(value));
}

function sessionMinuteLabel(value: string): string {
  const label = minuteLabel(value);
  const [hours, minutes] = label.split(":").map(Number);
  const minute = hours * 60 + minutes;
  if (!Number.isFinite(minute) || minute < 570) return "09:30";
  if (minute <= 690) return label;
  if (minute < 780) return "11:30";
  if (minute <= 900) return label;
  return "15:00";
}

function previousClose(data: StockTimelineResponse): number | null {
  const prior = data.bars
    .filter((bar) => bar.trade_date < data.as_of)
    .sort((left, right) => left.trade_date.localeCompare(right.trade_date))
    .at(-1);
  const value = prior ? Number(prior.close) : Number.NaN;
  return Number.isFinite(value) ? value : null;
}

export function stockIntradayOption(data: StockTimelineResponse): EChartsOption {
  const points = [...(data.intraday_points ?? [])]
    .sort((left, right) => left.observed_at.localeCompare(right.observed_at));
  const byMinute = new Map(points.map((point) => [sessionMinuteLabel(point.observed_at), point]));
  const close = previousClose(data);
  const minutePoints = SESSION_LABELS.map((label) => byMinute.get(label) ?? null);
  const prices = minutePoints.map((point) => {
    const value = Number(point?.price);
    return Number.isFinite(value) ? value : null;
  });
  const validPriceCount = prices.filter((value): value is number => value !== null).length;
  let priorVolume: number | null = null;
  let priorPrice = close;
  const volumeColors: string[] = [];
  const volumes = minutePoints.map((point) => {
    if (!point) {
      volumeColors.push(chartTheme.mutedTextColor);
      return null;
    }
    const currentPrice = Number(point.price);
    const up = Number.isFinite(currentPrice) && priorPrice !== null
      ? currentPrice >= priorPrice
      : Number(point.change_percent) >= 0;
    volumeColors.push(up ? chartTheme.upColor : chartTheme.downColor);
    if (Number.isFinite(currentPrice)) priorPrice = currentPrice;

    const currentVolume = Number(point.volume);
    if (!Number.isFinite(currentVolume)) return null;
    if (priorVolume === null) {
      priorVolume = currentVolume;
      return null;
    }
    const increment = currentVolume >= priorVolume ? currentVolume - priorVolume : currentVolume;
    priorVolume = currentVolume;
    return increment;
  });
  const latestPrice = Number(points.at(-1)?.price);
  const lineColor = close !== null && Number.isFinite(latestPrice) && latestPrice < close
    ? chartTheme.downColor
    : chartTheme.upColor;
  const closeGuide = close === null ? [] : [{
    name: "昨收",
    yAxis: close,
    lineStyle: { color: chartTheme.warningColor, type: "dashed" as const, width: 1, opacity: .75 },
    label: { show: true, formatter: `昨收 ${close.toFixed(2)}`, color: chartTheme.warningColor, position: "insideEndTop" as const },
  }];

  return {
    animation: false,
    backgroundColor: chartTheme.backgroundColor,
    grid: [
      { left: 52, right: 18, top: 28, bottom: 88 },
      { left: 52, right: 18, height: 44, bottom: 28 },
    ],
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: chartTheme.tooltipBackgroundColor,
      borderColor: chartTheme.liveColor,
      textStyle: { color: chartTheme.textColor, fontFamily: chartTheme.fontFamily, fontSize: 12 },
    },
    xAxis: [
      {
        type: "category",
        data: SESSION_LABELS,
        boundaryGap: false,
        axisLabel: { color: chartTheme.mutedTextColor, interval: 0, formatter: (value: string) => MAJOR_TIMES.has(value) ? value : "" },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: chartTheme.gridColor } },
      },
      { type: "category", gridIndex: 1, data: SESSION_LABELS, boundaryGap: true, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
    ],
    yAxis: [
      { type: "value", scale: true, axisLabel: { color: chartTheme.mutedTextColor }, splitLine: { lineStyle: { color: chartTheme.gridColor } } },
      { type: "value", gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } },
    ],
    series: [
      {
        name: "价格",
        type: "line",
        data: prices,
        connectNulls: false,
        // A post-close fallback can contain exactly one real snapshot. Keep
        // that point visible instead of rendering an empty-looking chart.
        showSymbol: validPriceCount <= 1,
        symbol: "circle",
        symbolSize: validPriceCount <= 1 ? 8 : 0,
        lineStyle: { color: lineColor, width: 2, shadowBlur: 8, shadowColor: `${lineColor}55` },
        itemStyle: { color: lineColor },
        areaStyle: { color: `${lineColor}12` },
        markLine: { symbol: ["none", "none"], silent: true, data: closeGuide },
      },
      {
        name: "成交量",
        type: "bar",
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: {
          color: ({ dataIndex }: { dataIndex: number }) => volumeColors[dataIndex],
        },
      },
    ],
  };
}

function movingAverage(bars: StockTimelineBar[], window: number): Array<number | null> {
  return bars.map((_, index) => {
    if (index + 1 < window) return null;
    const values = bars.slice(index + 1 - window, index + 1).map((bar) => Number(bar.close));
    if (values.some((value) => !Number.isFinite(value))) return null;
    return Number((values.reduce((sum, value) => sum + value, 0) / window).toFixed(3));
  });
}

export function stockThirtyDayOption(data: StockTimelineResponse): EChartsOption {
  const bars = [...data.bars]
    .sort((left, right) => left.trade_date.localeCompare(right.trade_date))
    .slice(-30);
  const dates = bars.map((bar) => bar.trade_date);
  const candles = bars.map((bar) => [Number(bar.open), Number(bar.close), Number(bar.low), Number(bar.high)]);
  const volumeColors = bars.map((bar) => Number(bar.close) >= Number(bar.open) ? chartTheme.upColor : chartTheme.downColor);
  const averageSeries = ([5, 10, 20] as const).map((window, index) => ({
    name: `MA${window}`,
    type: "line" as const,
    data: movingAverage(bars, window),
    showSymbol: false,
    smooth: false,
    lineStyle: { width: 1.35, color: [chartTheme.liveColor, chartTheme.warningColor, "#a78bfa"][index] },
  }));

  return {
    animation: false,
    backgroundColor: chartTheme.backgroundColor,
    legend: { top: 1, right: 12, textStyle: { color: chartTheme.mutedTextColor, fontFamily: chartTheme.fontFamily }, data: ["MA5", "MA10", "MA20"] },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
      confine: true,
      backgroundColor: chartTheme.tooltipBackgroundColor,
      borderColor: chartTheme.liveColor,
      textStyle: { color: chartTheme.textColor, fontFamily: chartTheme.fontFamily, fontSize: 12 },
    },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 52, right: 18, top: 34, bottom: 92 },
      { left: 52, right: 18, height: 46, bottom: 30 },
    ],
    xAxis: [
      { type: "category", data: dates, boundaryGap: true, axisLabel: { color: chartTheme.mutedTextColor, hideOverlap: true }, axisTick: { show: false }, axisLine: { lineStyle: { color: chartTheme.gridColor } } },
      { type: "category", gridIndex: 1, data: dates, boundaryGap: true, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
    ],
    yAxis: [
      { type: "value", scale: true, axisLabel: { color: chartTheme.mutedTextColor }, splitLine: { lineStyle: { color: chartTheme.gridColor } } },
      { type: "value", gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } },
    ],
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 },
      { type: "slider", xAxisIndex: [0, 1], height: 12, bottom: 5, borderColor: chartTheme.gridColor, fillerColor: "rgba(57,200,221,.12)", textStyle: { color: chartTheme.mutedTextColor } },
    ],
    series: [
      { name: "日 K", type: "candlestick", data: candles, itemStyle: { color: chartTheme.upColor, color0: chartTheme.downColor, borderColor: chartTheme.upColor, borderColor0: chartTheme.downColor } },
      ...averageSeries,
      { name: "成交量", type: "bar", data: bars.map((bar) => bar.volume), xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: ({ dataIndex }: { dataIndex: number }) => volumeColors[dataIndex] } },
    ],
  };
}

function intradayEmptyText(data: StockTimelineResponse): string {
  const warning = data.intraday_warnings?.[0];
  if (warning === "market_not_open") return "等待开盘，开盘后自动显示真实分时";
  if (warning === "market_closed") return "当前休市，没有当日分时数据";
  if (data.intraday_status === "waiting") return "正在等待首个真实采样点";
  if (warning === "intraday_snapshot_read_failed") return "分时数据读取失败，日线仍可正常查看";
  return "当日没有已归档的真实分时数据";
}

export function StockTimeframeCharts({ data }: { data: StockTimelineResponse }) {
  const points = data.intraday_points ?? [];
  const intradayReady = data.intraday_status === "ready" && points.length > 0;
  const dailyReady = data.bars.length > 0;
  const latestPoint = points.at(-1);
  const latestBar = [...data.bars].sort((left, right) => left.trade_date.localeCompare(right.trade_date)).at(-1);

  return <section className="stock-timeframe-grid" aria-label="个股分时与近三十日行情">
    <article className="terminal-panel stock-timeframe-card intraday-card">
      <header><div><Activity size={17} /><span><p>INTRADAY</p><h2>当日分时</h2></span></div><small>{latestPoint ? `${minuteLabel(latestPoint.observed_at)} · ${latestPoint.source}` : "真实采样"}</small></header>
      {intradayReady
        ? <QuantChart option={stockIntradayOption(data)} ariaLabel={`${data.symbol} 当日分时行情`} />
        : <div className="stock-timeframe-empty"><Activity size={22} /><b>{intradayEmptyText(data)}</b><span>不会使用模拟走势补位</span></div>}
    </article>
    <article className="terminal-panel stock-timeframe-card daily-card">
      <header><div><BarChart3 size={17} /><span><p>30 TRADING DAYS</p><h2>近 30 交易日</h2></span></div><small>{latestBar ? `更新至 ${latestBar.trade_date}` : "本地历史库"}</small></header>
      {dailyReady
        ? <QuantChart option={stockThirtyDayOption(data)} ariaLabel={`${data.symbol} 近 30 交易日日 K 线`} />
        : <div className="stock-timeframe-empty"><BarChart3 size={22} /><b>本地日线尚未就绪</b><span>完成日线修复后自动显示</span></div>}
    </article>
  </section>;
}
