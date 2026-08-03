import type { OverviewSentiment } from "./types";

function clampScore(value: string | null): number {
  const score = Number(value);
  return Number.isFinite(score) ? Math.min(100, Math.max(0, score)) : 0;
}

function bandLabel(value: string): string {
  return ({
    panic: "恐慌",
    cold: "低迷",
    neutral: "中性",
    active: "活跃",
    overheated: "过热",
    unavailable: "数据不足",
  } as Record<string, string>)[value] ?? value;
}

export function MarketTemperatureGauge({ sentiment }: { sentiment: OverviewSentiment }) {
  const score = clampScore(sentiment.score);
  return <div className="overview-gauge" aria-label={`市场情绪 ${sentiment.score ?? "不可用"}`}>
    <div className="overview-gauge-arc" style={{ "--gauge-score": `${score * 1.8}deg` } as React.CSSProperties}>
      <span className="overview-gauge-mask" />
      <i style={{ transform: `rotate(${score * 1.8 - 90}deg)` }} />
    </div>
    <div className="overview-gauge-value"><strong>{sentiment.score ?? "--"}</strong><span>{bandLabel(sentiment.band || "unavailable")}</span></div>
    <small>覆盖 {sentiment.coverage_percent}%</small>
  </div>;
}
