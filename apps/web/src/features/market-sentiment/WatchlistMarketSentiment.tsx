import { Activity, AlertTriangle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import type { MarketSentimentResponse, SentimentBand } from "./types";

type Props = {
  load: () => Promise<MarketSentimentResponse>;
};

type State =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "ready"; response: MarketSentimentResponse };

const bandNames: Record<SentimentBand, string> = {
  panic: "恐慌",
  cold: "低迷",
  neutral: "中性",
  active: "活跃",
  overheated: "过热",
  unavailable: "不可用",
};

function rounded(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.round(parsed) : null;
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间不可用";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

export function WatchlistMarketSentiment({ load }: Props) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ kind: "loading" });
    load()
      .then((response) => { if (active) setState({ kind: "ready", response }); })
      .catch(() => { if (active) setState({ kind: "error" }); });
    return () => { active = false; };
  }, [attempt, load]);

  const item = state.kind === "ready"
    ? state.response.current ?? state.response.previous_close
    : null;
  const score = rounded(item?.score);
  const unavailable = !item || score === null || item.band === "unavailable";
  const band = unavailable ? "unavailable" : item.band;
  const coverage = rounded(item?.coverage_percent);
  const quality = item?.quality === "ready"
    ? "数据完整"
    : item?.quality === "partial" ? "部分可用" : "暂不可评分";
  const phase = state.kind === "ready" && state.response.display_mode === "previous_close_baseline"
    ? "昨收基线"
    : item?.phase === "postclose" ? "盘后定稿" : "盘中观测";

  return <section
    className={`watchlist-market-sentiment watchlist-sentiment-band-${band}`}
    role="region"
    aria-label="自选股市场环境"
  >
    <header className="watchlist-sentiment-heading">
      <Activity size={16} aria-hidden="true" />
      <span><b>A 股全市场环境</b><small>不是个股评分</small></span>
    </header>

    {state.kind === "loading" && <div className="watchlist-sentiment-state" role="status" aria-busy="true">
      <span>正在读取市场情绪...</span>
    </div>}

    {state.kind === "error" && <div className="watchlist-sentiment-state error" role="alert">
      <AlertTriangle size={17} aria-hidden="true" />
      <span><b>市场情绪暂不可用</b><small>自选股仍可正常查看。</small></span>
      <button type="button" onClick={() => setAttempt((value) => value + 1)}>
        <RefreshCw size={15} aria-hidden="true" />重试市场情绪
      </button>
    </div>}

    {state.kind === "ready" && <div className="watchlist-sentiment-content">
      <div className="watchlist-sentiment-reading">
        {unavailable
          ? <strong className="watchlist-sentiment-unavailable">暂不可用</strong>
          : <span className="watchlist-sentiment-score"><strong data-testid="watchlist-sentiment-score">{score}</strong><small>/ 100</small></span>}
        <span className="watchlist-sentiment-band"><b>{unavailable ? "数据不足" : bandNames[band]}</b><small>{phase}</small></span>
      </div>
      <div className="watchlist-sentiment-context">
        <p>{item?.beginner_guidance || "等待核心行情来源恢复后再判断。"}</p>
        <footer>
          <span>覆盖率 {coverage === null ? "--" : coverage}% · {quality}</span>
          {item?.freshness === "stale" && <strong>历史参考</strong>}
          {item && <time dateTime={item.observed_at}>数据截至 {formatTime(item.observed_at)}</time>}
        </footer>
      </div>
    </div>}
  </section>;
}
