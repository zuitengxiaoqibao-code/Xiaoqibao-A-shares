import { AlertTriangle, ExternalLink } from "lucide-react";

import type {
  AlertUrgency,
  AssociationKind,
  BreakingNewsAlert,
  ImpactDirection,
  VerificationState,
} from "./types";


const urgencyLabels: Record<AlertUrgency, string> = {
  breaking: "突发",
  tracking: "跟踪",
  normal: "常规",
};
const verificationLabels: Record<VerificationState, string> = {
  multi_source_confirmed: "多源确认",
  verified: "已核验",
  pending: "待核验",
  unverified: "未核验",
};
const associationLabels: Record<AssociationKind, string> = {
  direct: "直接关联",
  context: "上下文关联",
  theme: "题材关联",
  macro: "宏观",
};
const directionLabels: Record<ImpactDirection, string> = {
  positive: "偏正面",
  negative: "偏负面",
  neutral: "中性",
  uncertain: "方向待核验",
};

interface BreakingNewsStripProps {
  alerts: BreakingNewsAlert[];
  loading: boolean;
  error: string | null;
  onOpenAShare?: (symbol: string) => void;
}


function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}


export function BreakingNewsStrip({
  alerts,
  loading,
  error,
  onOpenAShare,
}: BreakingNewsStripProps) {
  return (
    <section className="terminal-panel breaking-news-strip" aria-label="突发事件">
      <header className="terminal-panel-header">
        <div className="terminal-panel-heading">
          <strong className="terminal-panel-title">重要事件雷达</strong>
          <span className="terminal-panel-subtitle">核验状态、股票关联与来源可追溯</span>
        </div>
        <span className="breaking-news-strip__count">
          {loading ? "正在刷新" : `${alerts.length} 条`}
        </span>
      </header>
      {error ? <p className="breaking-news-strip__notice" role="status">{error}</p> : null}
      {!alerts.length ? (
        <div className="breaking-news-strip__empty" role="status">
          {loading ? "正在读取已归档新闻证据" : "当前没有符合核验与关联规则的提醒"}
        </div>
      ) : (
        <div className="breaking-news-strip__rail">
          {alerts.map((alert) => (
            <article
              className="breaking-news-card"
              data-urgency={alert.urgency}
              data-direction={alert.impact_direction}
              key={alert.event_id}
            >
              <div className="breaking-news-card__badges">
                <span>{urgencyLabels[alert.urgency]}</span>
                <span>{verificationLabels[alert.verification_state]}</span>
                <span>{associationLabels[alert.association_kind]}</span>
              </div>
              <div className="breaking-news-card__meta">
                <time dateTime={alert.occurred_at}>{formatTime(alert.occurred_at)}</time>
                <span>{alert.source_count} 个来源</span>
              </div>
              <h3>{alert.headline}</h3>
              <div className="breaking-news-card__direction">
                <AlertTriangle aria-hidden="true" size={14} />
                {alert.ai_degraded ? "AI 方向待核验" : directionLabels[alert.impact_direction]}
                {!alert.ai_degraded && alert.impact_confidence
                  ? ` · 可信度 ${Math.round(Number(alert.impact_confidence) * 100)}%`
                  : null}
              </div>
              <div className="breaking-news-card__symbols">
                {alert.affected_symbols.map((symbol) => onOpenAShare ? (
                  <button key={symbol} type="button" onClick={() => onOpenAShare(symbol)} aria-label={`查看股票 ${symbol}`}>
                    {symbol}
                  </button>
                ) : <span key={symbol}>{symbol}</span>)}
              </div>
              <footer>
                <span title={alert.publishers.join(" / ")}>{alert.publishers.join(" / ")}</span>
                <a href={alert.source_urls[0]} target="_blank" rel="noreferrer">
                  查看原始来源 <ExternalLink aria-hidden="true" size={13} />
                </a>
              </footer>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
