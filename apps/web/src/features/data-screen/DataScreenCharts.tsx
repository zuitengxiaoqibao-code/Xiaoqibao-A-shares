import type { EChartsOption } from "echarts";
import { useEffect, useMemo, useState } from "react";

import type { DataScreenModel } from "./types";
import type { BreakingNewsAlertResponse } from "../news-alerts/types";
import { QuantChart } from "../quant-analysis/QuantChart";

function signed(value: number): string {
  if (!Number.isFinite(value)) return "--";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function toneClass(tone: DataScreenModel["indices"][number]["tone"]): string {
  return tone === "up" ? "data-screen-up" : tone === "down" ? "data-screen-down" : tone === "flat" ? "data-screen-flat" : "data-screen-unavailable";
}

function numeric(value: number | null): number { return value === null || !Number.isFinite(value) ? 0 : value; }

function formatNewsTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "--:--" : new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
}

function verificationLabel(value: BreakingNewsAlertResponse["alerts"][number]["verification_state"]): string {
  return value === "verified" || value === "multi_source_confirmed" ? "已核验" : value === "pending" ? "待核验" : "未核验";
}

function impactLabel(value: BreakingNewsAlertResponse["alerts"][number]["impact_direction"]): string {
  return value === "positive" ? "正向" : value === "negative" ? "负向" : value === "neutral" ? "中性" : "待确认";
}

const TREND_INDICES = [
  { instrument: "sh000001", title: "上证指数趋势" },
  { instrument: "sz399001", title: "深圳成指趋势" },
  { instrument: "sz399006", title: "创业板指趋势" },
] as const;

export function DataScreenCharts({ model, newsAlerts = [], showNews = true }: { model: DataScreenModel; newsAlerts?: BreakingNewsAlertResponse["alerts"]; showNews?: boolean }) {
  const [activeInstrument, setActiveInstrument] = useState<string>(TREND_INDICES[0].instrument);
  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveInstrument((current) => {
        const index = TREND_INDICES.findIndex((item) => item.instrument === current);
        return TREND_INDICES[(index + 1) % TREND_INDICES.length].instrument;
      });
    }, 10_000);
    return () => window.clearInterval(timer);
  }, []);
  const activeTrend = useMemo(
    () => TREND_INDICES.find((item) => item.instrument === activeInstrument) ?? TREND_INDICES[0],
    [activeInstrument],
  );
  const activeMinuteSeries = model.minuteSeriesByIndex[activeTrend.instrument]
    ?? (activeTrend.instrument === "sh000001" ? model.minuteSeries : []);
  const lineOption: EChartsOption = {
    animation: true, animationDuration: 500, animationDurationUpdate: 450,
    grid: { left: 38, right: 10, top: 16, bottom: 18 },
    tooltip: { trigger: "axis", transitionDuration: 0.18 },
    xAxis: { type: "category", data: activeMinuteSeries.map((point) => point.observed_at.slice(11, 16)), axisLabel: { color: "#78939d", fontSize: 12 }, axisLine: { lineStyle: { color: "#1a3542" } } },
    yAxis: { type: "value", scale: true, axisLabel: { color: "#78939d", fontSize: 12 }, splitLine: { lineStyle: { color: "rgba(57,214,206,.08)" } } },
    series: [{ type: "line", smooth: true, showSymbol: false, data: activeMinuteSeries.map((point) => point.price), lineStyle: { width: 2, color: "#39d6ce", shadowBlur: 10, shadowColor: "rgba(57,214,206,.9)" }, areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(57,214,206,.48)" }, { offset: .55, color: "rgba(77,163,255,.18)" }, { offset: 1, color: "rgba(57,214,206,0)" }] } }, animationDelay: (index: number) => index * 5 }],
  };
  const sectorOption: EChartsOption = {
    animation: true, animationDurationUpdate: 500,
    grid: { left: 54, right: 12, top: 12, bottom: 22 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, transitionDuration: 0.18 },
    xAxis: { type: "category", data: model.sectors.slice(0, 6).map((sector) => sector.name), axisLabel: { color: "#78939d", fontSize: 12, interval: 0 }, axisLine: { lineStyle: { color: "#1a3542" } } },
    yAxis: { type: "value", axisLabel: { color: "#78939d", fontSize: 12 }, splitLine: { lineStyle: { color: "rgba(57,214,206,.08)" } } },
    series: [{ type: "bar", barWidth: 16, data: model.sectors.slice(0, 6).map((sector) => ({ value: numeric(Number(sector.change_percent)), itemStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: numeric(Number(sector.change_percent)) >= 0 ? [{ offset: 0, color: "#ff7480" }, { offset: 1, color: "#b51f48" }] : [{ offset: 0, color: "#56e0a2" }, { offset: 1, color: "#147c75" }] }, shadowBlur: 12, shadowColor: numeric(Number(sector.change_percent)) >= 0 ? "rgba(240,91,102,.7)" : "rgba(57,200,135,.6)" } })) }],
  };
  const sectorPalette = ["#4da3ff", "#39d6ce", "#f2c96d", "#c084fc", "#ff7480", "#56e0a2", "#7dd3fc", "#fb923c", "#a78bfa", "#f472b6", "#34d399", "#facc15"];
  const capitalShareOption: EChartsOption = {
    animation: true, animationDurationUpdate: 500,
    tooltip: { trigger: "item", transitionDuration: 0.18 },
    legend: { bottom: 0, left: "center", textStyle: { color: "#78939d", fontSize: 12 } },
    series: [{ type: "pie", radius: ["38%", "66%"], center: ["50%", "43%"], label: { color: "#cfe1e5", fontSize: 12 }, data: model.sectors.slice(0, 12).map((sector, index) => ({ name: sector.name, value: numeric(Number(sector.amount_yi)), itemStyle: { color: sectorPalette[index % sectorPalette.length] } })) }],
  };
  return <div className={`data-screen-chart-stack${showNews ? " has-news" : ""}`}><section className="data-screen-chart-index"><header>{activeTrend.title} · 实时轮换</header><div className="data-screen-index-strip">{TREND_INDICES.map((trend) => { const index = model.indices.find((item) => item.instrument === trend.instrument); return <div key={trend.instrument} data-testid={`data-screen-index-trend-${trend.instrument}`} aria-current={trend.instrument === activeInstrument ? "true" : undefined} className={`data-screen-index-trend ${trend.instrument === activeInstrument ? "is-active" : ""} ${toneClass(index?.tone ?? "unavailable")}`}><b>{trend.title}</b><strong>{index?.value || "--"}</strong><span>{index ? signed(Number(index.change_percent)) : "--"}</span></div>; })}{model.indices.length === 0 && <span className="data-screen-inline-empty">指数数据暂未接入</span>}</div>{activeMinuteSeries.length ? <QuantChart option={lineOption} ariaLabel="指数趋势图" /> : <div className="data-screen-chart-empty">{activeTrend.title}分钟数据暂未接入</div>}</section><section className="data-screen-chart-sector"><header>板块涨幅</header><QuantChart option={sectorOption} ariaLabel="板块涨幅柱状图" /></section><section className="data-screen-chart-capital-share"><header>板块成交额占比 · 北向资金待接入</header>{model.sectors.length ? <QuantChart option={capitalShareOption} ariaLabel="板块成交额占比图" /> : <div className="data-screen-chart-empty">板块成交额暂无有效数据<br /><small>北向资金（沪股通 + 深股通）当前来源未提供</small></div>}</section>{showNews && <section className="data-screen-chart-news" role="region" aria-label="数据大屏新闻"><header>实时新闻 · 关联标的</header>{newsAlerts.length > 0 ? <div className="data-screen-chart-news-list">{newsAlerts.slice(0, 10).map((item) => <div key={item.event_id}><time>{formatNewsTime(item.occurred_at)}</time><b>{item.headline}</b>{item.affected_symbols[0] && <em>{item.affected_symbols[0]}</em>}<span className="data-screen-chart-news-tags"><small className={`data-screen-news-tag data-screen-news-tag-${item.verification_state}`}>{verificationLabel(item.verification_state)}</small>{item.affected_symbols.length > 0 && <small className="data-screen-news-tag data-screen-news-tag-tracking">跟踪</small>}<small className={`data-screen-news-tag data-screen-news-tag-${item.impact_direction}`}>{impactLabel(item.impact_direction)}</small></span></div>)}</div> : <div className="data-screen-chart-news-empty">暂无已验证快讯</div>}</section>}</div>;
}
