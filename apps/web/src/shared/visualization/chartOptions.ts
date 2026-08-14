import type { EChartsOption } from "echarts";

import { chartTheme, chartToneColor } from "./chartTheme";
import type { MetricTone } from "./types";

type NullableNumber = number | null;

type NamedSeries = {
  name: string;
  values: NullableNumber[];
};

type RadarInput = {
  indicators: Array<{ name: string; max: number }>;
  values: NullableNumber[];
  name?: string;
};

const grid = chartTheme.gridColor;
const text = chartTheme.textColor;
const muted = chartTheme.mutedTextColor;

function baseOption(): Pick<EChartsOption, "animation" | "textStyle" | "tooltip"> {
  return {
    animation: false,
    textStyle: { color: text, fontFamily: chartTheme.fontFamily },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#071018",
      borderColor: chartTheme.liveColor,
      textStyle: { color: text, fontFamily: chartTheme.fontFamily },
    },
  };
}

function categoryAxis(data: string[]) {
  return {
    type: "category" as const,
    data,
    axisLine: { lineStyle: { color: grid } },
    axisTick: { show: false },
    axisLabel: { color: muted, hideOverlap: true },
  };
}

function valueAxis() {
  return {
    type: "value" as const,
    scale: true,
    axisLine: { show: false },
    axisLabel: { color: muted },
    splitLine: { lineStyle: { color: grid } },
  };
}

export function buildBarLineOption({ categories, bars, lines }: {
  categories: string[];
  bars: NamedSeries[];
  lines: NamedSeries[];
}): EChartsOption {
  return {
    ...baseOption(),
    grid: { left: 52, right: 22, top: 30, bottom: 34 },
    xAxis: categoryAxis(categories),
    yAxis: valueAxis(),
    series: [
      ...bars.map((item) => ({
        name: item.name,
        type: "bar" as const,
        data: item.values,
        barMaxWidth: 16,
        itemStyle: { color: chartTheme.warningColor },
      })),
      ...lines.map((item) => ({
        name: item.name,
        type: "line" as const,
        data: item.values,
        connectNulls: false,
        symbol: "none",
        smooth: 0.15,
        lineStyle: { color: chartTheme.liveColor, width: 2 },
      })),
    ],
  };
}

export function buildDualAxisOption({ categories, primary, secondary, primaryTone = "up", secondaryTone = "neutral" }: {
  categories: string[];
  primary: NamedSeries;
  secondary: NamedSeries;
  primaryTone?: MetricTone;
  secondaryTone?: MetricTone;
}): EChartsOption {
  return {
    ...baseOption(),
    grid: { left: 52, right: 52, top: 30, bottom: 34 },
    xAxis: categoryAxis(categories),
    yAxis: [valueAxis(), { ...valueAxis(), position: "right" as const, splitLine: { show: false } }],
    series: [
      {
        name: primary.name,
        type: "line" as const,
        data: primary.values,
        connectNulls: false,
        symbol: "none",
        lineStyle: { color: chartToneColor(primaryTone), width: 2 },
        itemStyle: { color: chartToneColor(primaryTone) },
        yAxisIndex: 0,
      },
      {
        name: secondary.name,
        type: "bar" as const,
        data: secondary.values,
        barMaxWidth: 18,
        itemStyle: { color: chartToneColor(secondaryTone) },
        yAxisIndex: 1,
      },
    ],
  };
}

export function buildRadarOption({ indicators, values, name = "指标" }: RadarInput): EChartsOption {
  return {
    ...baseOption(),
    tooltip: { trigger: "item" },
    radar: {
      radius: "66%",
      splitNumber: 4,
      indicator: indicators,
      axisName: { color: muted, fontSize: 12 },
      splitLine: { lineStyle: { color: [grid] } },
      splitArea: { areaStyle: { color: ["rgba(11,18,28,.30)", "rgba(15,26,39,.20)"] } },
      axisLine: { lineStyle: { color: grid } },
    },
    series: [{
      type: "radar" as const,
      data: [{ value: values, name }],
      symbolSize: 5,
      lineStyle: { color: chartTheme.warningColor, width: 2 },
      itemStyle: { color: chartTheme.warningColor },
      areaStyle: { color: "rgba(229,184,75,.16)" },
    }],
  };
}

export function buildHorizontalRankOption({ categories, values, name, tone = "live" }: {
  categories: string[];
  values: NullableNumber[];
  name: string;
  tone?: MetricTone;
}): EChartsOption {
  return {
    ...baseOption(),
    grid: { left: 86, right: 30, top: 22, bottom: 28 },
    xAxis: valueAxis(),
    yAxis: { ...categoryAxis(categories), inverse: true },
    series: [{
      name,
      type: "bar" as const,
      data: values,
      barMaxWidth: 18,
      itemStyle: { color: chartToneColor(tone) },
      label: { show: true, position: "right" as const, color: text, fontSize: 12 },
    }],
  };
}

export function buildStackedCompositionOption({ categories, series }: {
  categories: string[];
  series: Array<NamedSeries & { tone: MetricTone }>;
}): EChartsOption {
  return {
    ...baseOption(),
    grid: { left: 52, right: 22, top: 34, bottom: 34 },
    legend: { top: 0, textStyle: { color: muted, fontSize: 12 } },
    xAxis: categoryAxis(categories),
    yAxis: valueAxis(),
    series: series.map((item) => ({
      name: item.name,
      type: "bar" as const,
      stack: "composition",
      data: item.values,
      barMaxWidth: 34,
      itemStyle: { color: chartToneColor(item.tone) },
    })),
  };
}

export function buildFactorOption(input: RadarInput): EChartsOption {
  if (input.indicators.length <= 8) return buildRadarOption(input);
  return buildHorizontalRankOption({
    categories: input.indicators.map((item) => item.name),
    values: input.values,
    name: input.name ?? "指标",
    tone: "warning",
  });
}

export function buildHeatmapOption({ x, y, values }: {
  x: string[];
  y: string[];
  values: Array<[number, number, NullableNumber]>;
}): EChartsOption {
  return {
    ...baseOption(),
    tooltip: { position: "top" },
    grid: { left: 70, right: 22, top: 18, bottom: 48 },
    xAxis: { ...categoryAxis(x), splitArea: { show: true } },
    yAxis: { ...categoryAxis(y), splitArea: { show: true } },
    visualMap: {
      min: -10,
      max: 10,
      calculable: false,
      orient: "horizontal",
      left: "center",
      bottom: 4,
      textStyle: { color: muted },
      inRange: { color: [chartTheme.downColor, "#182b3e", chartTheme.upColor] },
    },
    series: [{ type: "heatmap" as const, data: values, label: { show: true, color: text, fontSize: 12 } }],
  };
}

export function buildTreemapOption({ data }: { data: Array<{ name: string; value: NullableNumber; children?: Array<{ name: string; value: NullableNumber }> }> }): EChartsOption {
  return {
    ...baseOption(),
    tooltip: { trigger: "item" },
    series: [{
      type: "treemap" as const,
      roam: false,
      nodeClick: false,
      breadcrumb: { show: false },
      label: { show: true, color: text, fontFamily: chartTheme.fontFamily },
      itemStyle: { borderColor: "#0b1118", borderWidth: 2, gapWidth: 2 },
      data,
    }] as unknown as EChartsOption["series"],
  };
}

export function buildGaugeOption({ value, name, max = 100, tone = "live" }: { value: NullableNumber; name: string; max?: number; tone?: MetricTone }): EChartsOption {
  const color = chartToneColor(tone);
  return {
    ...baseOption(),
    tooltip: { show: false },
    series: [{
      type: "gauge" as const,
      min: 0,
      max,
      startAngle: 210,
      endAngle: -30,
      progress: { show: value !== null, width: 12, itemStyle: { color } },
      axisLine: { lineStyle: { width: 12, color: [[1, "#22313d"]] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { show: value !== null, itemStyle: { color } },
      detail: { valueAnimation: false, color: value === null ? chartTheme.unavailableColor : color, fontFamily: chartTheme.fontFamily, fontSize: 22, offsetCenter: [0, "18%"], formatter: value === null ? "--" : "{value}" },
      title: { color: muted, fontSize: 12, offsetCenter: [0, "48%"] },
      data: [{ value, name }],
    }] as unknown as EChartsOption["series"],
  };
}

export function buildCandlestickOption({ categories, values, volume }: { categories: string[]; values: Array<[NullableNumber, NullableNumber, NullableNumber, NullableNumber]>; volume?: NullableNumber[] }): EChartsOption {
  const hasVolume = Array.isArray(volume);
  return {
    ...baseOption(),
    grid: hasVolume ? [{ left: 56, right: 24, top: 24, height: "60%" }, { left: 56, right: 24, top: "76%", height: "14%" }] : { left: 56, right: 24, top: 24, bottom: 36 },
    xAxis: hasVolume ? [categoryAxis(categories), { ...categoryAxis(categories), gridIndex: 1, axisLabel: { show: false } }] : categoryAxis(categories),
    yAxis: hasVolume ? [valueAxis(), { ...valueAxis(), gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } }] : valueAxis(),
    series: [
      { type: "candlestick" as const, data: values, itemStyle: { color: chartTheme.upColor, color0: chartTheme.downColor, borderColor: chartTheme.upColor, borderColor0: chartTheme.downColor } },
      ...(hasVolume ? [{ type: "bar" as const, name: "成交量", xAxisIndex: 1, yAxisIndex: 1, data: volume, itemStyle: { color: chartTheme.liveColor } }] : []),
    ],
  };
}
