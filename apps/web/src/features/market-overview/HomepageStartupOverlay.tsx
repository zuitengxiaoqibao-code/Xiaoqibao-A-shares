import type { MarketOverviewResponse } from "./types";

// Market data loads independently of the usable workspace. Missing quotes
// must never trap the user behind a startup dialog or simulated percentages.
export function HomepageStartupOverlay({ data, error, loading, snapshotReady = false, onRetry }: {
  data: MarketOverviewResponse | null;
  error: string | null;
  loading: boolean;
  liveReady?: boolean;
  snapshotReady?: boolean;
  hasCompletedInitialLoad?: boolean;
  onRetry: () => void;
}) {
  if (snapshotReady && !error) return null;
  return <section className="homepage-background-state" role="region" aria-label="首页后台数据状态" aria-live="polite">
    <span>{error ? data ? "最新数据更新失败，继续使用缓存" : "行情读取失败，页面仍可使用"
      : loading ? data ? "缓存已展示，正在后台更新最新数据" : "页面已就绪，正在后台读取市场快照"
      : "当前行情证据不足，可先使用其他页面"}</span>
    {error && <small>{error}</small>}
    {error && <button type="button" onClick={onRetry} disabled={loading} aria-label="重试首页数据">重新读取行情</button>}
  </section>;
}
