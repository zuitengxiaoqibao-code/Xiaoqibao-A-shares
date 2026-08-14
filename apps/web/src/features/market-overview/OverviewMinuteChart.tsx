import type { EChartsOption } from "echarts";

import { QuantChart } from "../quant-analysis/QuantChart";
import { chartTheme } from "../../shared/visualization/chartTheme";
import type { OverviewAnomaly, OverviewMinutePoint } from "./types";

function timeLabel(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit", minute: "2-digit", hour12: false,
    timeZone: "Asia/Shanghai",
  }).format(new Date(value));
}

const MAJOR_TIME_LABELS = new Set([
  "09:30", "10:00", "10:30", "11:00", "13:00", "13:30", "14:00", "14:30", "15:00",
]);

function tradingSessionLabels(): string[] {
  const labels: string[] = [];
  const appendRange = (startMinutes: number, endMinutes: number) => {
    for (let value = startMinutes; value <= endMinutes; value += 1) {
      const hour = Math.floor(value / 60).toString().padStart(2, "0");
      const minute = (value % 60).toString().padStart(2, "0");
      labels.push(`${hour}:${minute}`);
    }
  };
  appendRange(9 * 60 + 30, 11 * 60 + 30);
  appendRange(13 * 60, 15 * 60);
  return labels;
}

const TRADING_SESSION_LABELS = tradingSessionLabels();

const ATTRIBUTION_RULES: Array<{ pattern: RegExp; color: string }> = [
  { pattern: /机器人|工业|制造|军工|航天|航空|船舶|机械|自动化/i, color: chartTheme.eventColors.company },
  { pattern: /算力|人工智能|\bAI\b|半导体|芯片|软件|数据|通信|电子|信创|云计算/i, color: chartTheme.eventColors.policy },
  { pattern: /证券|券商|银行|保险|金融|多元金融/i, color: chartTheme.eventColors.industry },
  { pattern: /医药|医疗|创新药|生物|疫苗|中药|器械/i, color: chartTheme.eventColors.risk },
  { pattern: /消费|食品|饮料|白酒|零售|旅游|酒店|家电|纺织/i, color: chartTheme.eventColors.anomaly },
  { pattern: /新能源|光伏|储能|锂电|电池|风电|电力|煤炭|石油|有色/i, color: chartTheme.eventColors.financial },
  { pattern: /地产|房地产|基建|建筑|建材|水泥|交通|港口|公路/i, color: chartTheme.eventColors.capital },
  { pattern: /政策|央行|宏观|监管|会议|财政|产业政策/i, color: chartTheme.eventColors.policy },
];
const ATTRIBUTION_FALLBACK_COLORS = Object.values(chartTheme.eventColors);

export function anomalyAttributionColor(anomaly: OverviewAnomaly): string {
  const attribution = [...anomaly.themes, anomaly.label, anomaly.headline].filter(Boolean).join(" ");
  const matched = ATTRIBUTION_RULES.find(({ pattern }) => pattern.test(attribution));
  if (matched) return matched.color;
  const stableKey = anomaly.themes[0] || anomaly.label || anomaly.headline || anomaly.anomaly_id;
  let hash = 0;
  for (const character of stableKey) hash = ((hash * 31) + character.codePointAt(0)!) >>> 0;
  return ATTRIBUTION_FALLBACK_COLORS[hash % ATTRIBUTION_FALLBACK_COLORS.length];
}

type MatchedAnomaly = {
  anomaly: OverviewAnomaly;
  eventTime: number;
  nearestIndex: number;
  minute: string;
  price: number;
};

function matchAnomalies(points: OverviewMinutePoint[], anomalies: OverviewAnomaly[]): MatchedAnomaly[] {
  const pointTimes = points.map((point) => new Date(point.observed_at).getTime());
  if (pointTimes.length === 0) return [];
  return anomalies
    .map((anomaly) => {
      const eventTime = new Date(anomaly.occurred_at).getTime();
      if (!Number.isFinite(eventTime)) return null;
      let nearestIndex = 0;
      let nearestDistance = Number.POSITIVE_INFINITY;
      pointTimes.forEach((pointTime, index) => {
        const distance = Math.abs(pointTime - eventTime);
        if (distance < nearestDistance) {
          nearestDistance = distance;
          nearestIndex = index;
        }
      });
      if (nearestDistance > 90_000) return null;
      return {
        anomaly, eventTime, nearestIndex,
        minute: timeLabel(points[nearestIndex].observed_at),
        price: Number(points[nearestIndex].price),
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((left, right) => left.eventTime - right.eventTime);
}

export type AnomalyPulseGroup = {
  id: string;
  number: string;
  marker: string;
  lineLabel: string;
  minute: string;
  price: number;
  count: number;
  lane: 0 | 1;
  color: string;
  selected: boolean;
  events: OverviewAnomaly[];
};

function anomalyLineLabel(anomaly: OverviewAnomaly, extraCount = 0): string {
  const source = anomaly.label.trim() || anomaly.themes[0]?.trim() || anomaly.headline.trim() || "异动";
  const compact = source.replace(/[\s，。；：、,.!?！？:;]+/g, "").slice(0, 8);
  return `${[...compact].join("\n")}${extraCount > 0 ? `\n+${extraCount}` : ""}`;
}

export function buildAnomalyPulseGroups(
  points: OverviewMinutePoint[],
  anomalies: OverviewAnomaly[],
  selectedAnomalyId: string | null,
): AnomalyPulseGroup[] {
  const anomalyNumbers = new Map(numberedAnomalies(anomalies).map(({ event, number }) => [event.anomaly_id, number]));
  const grouped = new Map<string, MatchedAnomaly[]>();
  matchAnomalies(points, anomalies).forEach((item) => {
    const values = grouped.get(item.minute) ?? [];
    values.push(item);
    grouped.set(item.minute, values);
  });

  let previousTime = Number.NEGATIVE_INFINITY;
  let previousLane: 0 | 1 = 1;
  return Array.from(grouped.values())
    .sort((left, right) => left[0].eventTime - right[0].eventTime)
    .map((matches) => {
      const selected = matches.some(({ anomaly }) => anomaly.anomaly_id === selectedAnomalyId);
      const firstTime = matches[0].eventTime;
      const crowded = firstTime - previousTime <= 5 * 60_000;
      const lane: 0 | 1 = crowded ? (previousLane === 0 ? 1 : 0) : 0;
      previousTime = firstTime;
      previousLane = lane;
      const primary = matches.find(({ anomaly }) => anomaly.anomaly_id === selectedAnomalyId) ?? matches[0];
      const number = anomalyNumbers.get(primary.anomaly.anomaly_id) ?? "--";
      return {
        id: matches.map(({ anomaly }) => anomaly.anomaly_id).join("+"),
        number,
        marker: `${number}${matches.length > 1 ? ` +${matches.length - 1}` : ""}`,
        lineLabel: anomalyLineLabel(primary.anomaly, matches.length - 1),
        minute: primary.minute,
        price: primary.price,
        count: matches.length,
        lane,
        color: anomalyAttributionColor(primary.anomaly),
        selected,
        events: matches.map(({ anomaly }) => anomaly),
      };
    });
}

export function numberedAnomalies(anomalies: OverviewAnomaly[]): Array<{ event: OverviewAnomaly; number: string }> {
  return [...anomalies]
    .sort((left, right) => new Date(left.occurred_at).getTime() - new Date(right.occurred_at).getTime())
    .map((event, index) => ({ event, number: String(index + 1).padStart(2, "0") }));
}

export function overviewMinuteOption(
  points: OverviewMinutePoint[],
  anomalies: OverviewAnomaly[],
  selectedAnomalyId: string | null,
): EChartsOption {
  const pointsByTime = new Map(points.map((point) => [timeLabel(point.observed_at), point]));
  const prices = TRADING_SESSION_LABELS.map((label) => {
    const point = pointsByTime.get(label);
    return point ? Number(point.price) : null;
  });
  const volumes = TRADING_SESSION_LABELS.map((label) => {
    const point = pointsByTime.get(label);
    return point ? Number(point.volume) : null;
  });
  const pulseGroups = buildAnomalyPulseGroups(points, anomalies, selectedAnomalyId);
  const markerLines = pulseGroups.map((group) => ({
    name: group.number,
    xAxis: group.minute,
    lineStyle: { color: group.color, width: group.selected ? 2 : 1, type: "dashed" as const, opacity: group.selected ? .95 : .58 },
    label: {
      show: true, formatter: group.lineLabel, color: group.selected ? "#f8fafc" : group.color,
      backgroundColor: "rgba(6,15,24,.86)", borderColor: group.color, borderWidth: group.selected ? 1 : 0,
      borderRadius: 3, padding: [4, 3], fontSize: 13, fontWeight: group.selected ? 800 : 700,
      lineHeight: 15, rotate: 0,
      position: "middle" as const, offset: [group.lane ? 8 : 0, 0] as [number, number],
    },
  }));
  const anomalyPoints = pulseGroups.map((group) => ({
    name: group.marker,
    coord: [group.minute, group.price],
    itemStyle: { color: group.selected ? group.color : "#071119", borderColor: group.color, borderWidth: group.selected ? 3 : 2, shadowBlur: group.selected ? 18 : 8, shadowColor: group.color },
    symbolSize: group.selected ? 13 : 9,
  }));
  const selectedGroup = pulseGroups.find((group) => group.selected);
  const selectedPriceLine = selectedGroup ? {
    name: "selected-price",
    yAxis: selectedGroup.price,
    lineStyle: { color: selectedGroup.color, width: 1, type: "dotted" as const, opacity: .78 },
    label: {
      show: true, formatter: selectedGroup.price.toFixed(2), color: selectedGroup.color,
      backgroundColor: "#0c1720", borderColor: selectedGroup.color, borderWidth: 1,
      borderRadius: 4, padding: [2, 5], fontSize: 12, position: "insideEndTop" as const,
    },
  } : null;

  return {
    animation: false,
    grid: [{ left: 48, right: 16, top: 56, bottom: 84 }, { left: 48, right: 16, height: 44, bottom: 25 }],
    tooltip: {
      trigger: "axis", confine: true,
      backgroundColor: "rgba(5,14,22,.96)", borderColor: chartTheme.liveColor,
      textStyle: { color: chartTheme.textColor, fontFamily: chartTheme.fontFamily, fontSize: 12 },
    },
    xAxis: [
      {
        type: "category", data: TRADING_SESSION_LABELS, boundaryGap: false,
        axisLabel: { color: chartTheme.mutedTextColor, fontSize: 12, interval: 0, formatter: (value: string) => MAJOR_TIME_LABELS.has(value) ? value : "" },
        axisTick: { show: false }, axisLine: { lineStyle: { color: chartTheme.gridColor } },
      },
      { type: "category", data: TRADING_SESSION_LABELS, boundaryGap: true, gridIndex: 1, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
    ],
    yAxis: [
      { type: "value", scale: true, axisLabel: { color: chartTheme.mutedTextColor, fontSize: 12 }, splitLine: { lineStyle: { color: chartTheme.gridColor } } },
      { type: "value", gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } },
    ],
    series: [
      {
        name: "上证指数", type: "line", data: prices, showSymbol: false, smooth: false,
        lineStyle: { color: chartTheme.liveColor, width: 2 }, itemStyle: { color: chartTheme.liveColor },
        areaStyle: { color: "rgba(57,200,221,.08)" },
        markLine: {
          symbol: ["none", "none"], silent: true,
          data: selectedPriceLine ? [...markerLines, selectedPriceLine] : markerLines,
        },
        markPoint: { symbol: "circle", silent: true, label: { show: false }, data: anomalyPoints },
        markArea: selectedGroup ? {
          silent: true,
          itemStyle: { color: `${selectedGroup.color}12` },
          data: [[{ xAxis: selectedGroup.minute }, { xAxis: selectedGroup.minute }]],
        } : undefined,
      },
      { name: "成交量", type: "bar", data: volumes, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: "rgba(57,200,221,.28)" } },
    ],
  };
}

export function OverviewMinuteChart({ points, anomalies, selectedAnomalyId }: {
  points: OverviewMinutePoint[];
  anomalies: OverviewAnomaly[];
  selectedAnomalyId: string | null;
}) {
  if (points.length === 0) return <div className="overview-chart-empty">分时数据暂不可用</div>;
  return <QuantChart option={overviewMinuteOption(points, anomalies, selectedAnomalyId)} ariaLabel="上证指数分时图" />;
}
