import { AlertTriangle, CalendarClock, Link2, TrendingDown, TrendingUp } from "lucide-react";

import type { EventImpactReport, EventImpactTarget, EventImpactWindow } from "./types";

const horizons: EventImpactWindow["horizon_days"][] = [1, 3, 5, 20];
const impactStatus = { ready: "已核验", partial: "部分可用", unavailable: "不可用" } as const;

function ReturnValue({ window }: { window: EventImpactWindow }) {
  if (window.status !== "ready" || window.return_percent === null) {
    return <span className="event-impact-value unavailable">不可用</span>;
  }
  const numeric = Number(window.return_percent);
  const tone = numeric > 0 ? "positive" : numeric < 0 ? "negative" : "neutral";
  const Icon = numeric > 0 ? TrendingUp : numeric < 0 ? TrendingDown : CalendarClock;
  return <span className={`event-impact-value ${tone}`}><Icon size={14} />{numeric > 0 ? "+" : ""}{numeric.toFixed(2)}%</span>;
}

function Target({ target }: { target: EventImpactTarget }) {
  return <article className="event-impact-target" data-target-type={target.target_type} data-status={target.status}>
    <header><div><span>{target.target_type === "stock" ? "A股" : "板块"}</span><b>{target.target_id}</b></div><small>{impactStatus[target.status]}</small></header>
    <div className="event-impact-windows">
      {horizons.map((horizon) => {
        const window = target.windows.find((item) => item.horizon_days === horizon);
        return <div key={horizon} data-status={window?.status ?? "unavailable"}><span>{horizon}日</span><ReturnValue window={window ?? { horizon_days: horizon, status: "unavailable", baseline_trade_date: null, end_trade_date: null, baseline_close: null, end_close: null, return_percent: null, reason: "window_missing" }} />{window?.reason && <small>{window.reason.includes("sector_daily") ? "板块日线收益不可用" : window.reason}</small>}</div>;
      })}
    </div>
  </article>;
}

export function EventImpactPanel({ report }: { report: EventImpactReport }) {
  return <section className="event-impact-panel" role="region" aria-label="新闻事件影响复盘" data-status={report.status}>
    <header><div><span>EVENT IMPACT REVIEW</span><h3>事件影响复盘</h3></div><small>{impactStatus[report.status]}</small></header>
    <div className="event-impact-meta"><span><Link2 size={14} />{report.duplicate_status === "duplicate_cluster" ? `重复新闻 ${report.duplicate_article_count} 篇` : "单一来源"}</span><span>{report.association_status === "low_confidence" ? "关联置信度低" : report.association_status === "verified" ? "关联已核验" : "关联不可用"}</span><time>首次发布时间 {new Date(report.first_published_at).toLocaleString("zh-CN", { hour12: false })}</time></div>
    {report.targets.length > 0 ? <div className="event-impact-targets">{report.targets.map((target) => <Target key={`${target.target_type}-${target.target_id}`} target={target} />)}</div> : <div className="event-impact-empty"><AlertTriangle size={15} />没有真实关联标的，收益窗口不可用。</div>}
    {report.limitations.length > 0 && <footer>{report.limitations.join(" · ")}</footer>}
  </section>;
}
