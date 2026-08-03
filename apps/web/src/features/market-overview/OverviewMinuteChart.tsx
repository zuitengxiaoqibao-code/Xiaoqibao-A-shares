import type { EChartsOption } from "echarts";

import { QuantChart } from "../quant-analysis/QuantChart";
import type { OverviewAnomaly, OverviewMinutePoint } from "./types";

function timeLabel(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit", minute: "2-digit", hour12: false,
    timeZone: "Asia/Shanghai",
  }).format(new Date(value));
}

const ANOMALY_COLOR = "#96343d";
const SELECTED_ANOMALY_COLOR = "#d92131";
const UNVERIFIED_ANOMALY_COLOR = "#7b8794";
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

function verticalLabel(value: string): string {
  return Array.from(value.replace(/\s+/g, "")).join("\n");
}

function anomalyColor(anomaly: OverviewAnomaly, selected: boolean): string {
  if (selected) return SELECTED_ANOMALY_COLOR;
  return anomaly.direction === "uncertain" ? UNVERIFIED_ANOMALY_COLOR : ANOMALY_COLOR;
}

type AnomalyMarker = {
  name: string;
  xAxis: string;
  lineStyle: { color: string; width: number; type: "solid" | "dashed" };
  label: {
    show: true;
    formatter: string;
    color: string;
    fontSize: number;
    fontWeight: number;
    rotate: number;
    position: "insideEndTop";
    offset: [number, number];
    lineHeight: number;
  };
};

type MatchedAnomaly = {
  anomaly: OverviewAnomaly;
  eventTime: number;
  nearestIndex: number;
  lane: 0 | 1;
};

function matchAnomalies(
  points: OverviewMinutePoint[],
  anomalies: OverviewAnomaly[],
): MatchedAnomaly[] {
  const pointTimes = points.map((point) => new Date(point.observed_at).getTime());
  if (pointTimes.length === 0) return [];
  const matched = anomalies
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
      return { anomaly, eventTime, nearestIndex };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((a, b) => a.eventTime - b.eventTime);

  let previousTime = Number.NEGATIVE_INFINITY;
  let previousLane: 0 | 1 = 1;
  return matched.map((item) => {
    const isCrowded = item.eventTime - previousTime <= 5 * 60_000;
    const lane: 0 | 1 = isCrowded ? (previousLane === 0 ? 1 : 0) : 0;
    previousTime = item.eventTime;
    previousLane = lane;
    return { ...item, lane };
  });
}

export function buildAnomalyMarkers(
  points: OverviewMinutePoint[],
  anomalies: OverviewAnomaly[],
  selectedAnomalyId: string | null,
): AnomalyMarker[] {
  return matchAnomalies(points, anomalies)
    .map(({ anomaly, nearestIndex, lane }) => {
      const selected = selectedAnomalyId === anomaly.anomaly_id;
      const color = anomalyColor(anomaly, selected);
      return {
        name: anomaly.label,
        xAxis: timeLabel(points[nearestIndex].observed_at),
        lineStyle: { color, width: selected ? 2 : 1, type: selected ? "solid" : "dashed" },
        label: {
          show: true,
          formatter: verticalLabel(anomaly.label),
          color,
          fontSize: 12,
          fontWeight: selected ? 700 : 500,
          rotate: 0,
          position: "insideEndTop",
          offset: [0, lane * 148] as [number, number],
          lineHeight: 12,
        },
      };
    });
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
  const anomalyMarkers = buildAnomalyMarkers(points, anomalies, selectedAnomalyId);
  const anomalyPoints = matchAnomalies(points, anomalies).map(({ anomaly, nearestIndex }) => {
    const selected = selectedAnomalyId === anomaly.anomaly_id;
    return {
      name: anomaly.label,
      coord: [timeLabel(points[nearestIndex].observed_at), Number(points[nearestIndex].price)],
      itemStyle: {
        color: "#ffffff",
        borderColor: anomalyColor(anomaly, selected),
        borderWidth: selected ? 2 : 1.5,
      },
      symbolSize: selected ? 9 : 7,
    };
  });
  return {
    animation: false,
    grid: [{ left: 48, right: 16, top: 18, bottom: 84 }, { left: 48, right: 16, height: 44, bottom: 25 }],
    tooltip: { trigger: "axis", confine: true },
    xAxis: [
      {
        type: "category", data: TRADING_SESSION_LABELS, boundaryGap: false,
        axisLabel: {
          color: "#64748b", fontSize: 12, interval: 0,
          formatter: (value: string) => MAJOR_TIME_LABELS.has(value) ? value : "",
        },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#d5dce5" } },
      },
      { type: "category", data: TRADING_SESSION_LABELS, boundaryGap: true, gridIndex: 1, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
    ],
    yAxis: [
      { type: "value", scale: true, axisLabel: { color: "#64748b", fontSize: 12 }, splitLine: { lineStyle: { color: "#e7ebf0" } } },
      { type: "value", gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } },
    ],
    series: [
      {
        name: "上证指数", type: "line", data: prices, showSymbol: false, smooth: false,
        lineStyle: { color: "#1d9b4f", width: 2 }, itemStyle: { color: "#1d9b4f" },
        areaStyle: { color: "rgba(29,155,79,.04)" },
        markLine: {
          symbol: ["none", "none"], silent: true,
          lineStyle: { color: ANOMALY_COLOR, type: "dashed", width: 1 },
          label: { color: ANOMALY_COLOR, fontSize: 12, rotate: 0, position: "insideEndTop" },
          data: anomalyMarkers,
        },
        markPoint: {
          symbol: "circle", silent: true,
          label: { show: false },
          data: anomalyPoints,
        },
      },
      { name: "成交量", type: "bar", data: volumes, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: "rgba(38,111,168,.28)" } },
    ],
  };
}

export function OverviewMinuteChart({ points, anomalies, selectedAnomalyId }: {
  points: OverviewMinutePoint[];
  anomalies: OverviewAnomaly[];
  selectedAnomalyId: string | null;
}) {
  if (points.length === 0) {
    return <div className="overview-chart-empty">分时数据暂不可用</div>;
  }
  return <QuantChart
    option={overviewMinuteOption(points, anomalies, selectedAnomalyId)}
    ariaLabel="上证指数分时图"
  />;
}
