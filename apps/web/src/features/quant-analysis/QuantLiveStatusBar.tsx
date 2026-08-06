import { Clock3, Database, RadioTower } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { FirstLimitUpBoard } from "../first-limit-up/types";
import type { IntradayTick, QuantStrategyDashboard } from "./types";
import type { QuantLiveStatus } from "./useQuantLiveRefresh";

type Props = {
  board: FirstLimitUpBoard | null;
  boardStatus: QuantLiveStatus;
  boardLastSuccessAt: Date | null;
  latestTick: IntradayTick | null;
  tickStatus: QuantLiveStatus;
  strategy: QuantStrategyDashboard | null;
  strategyStatus: QuantLiveStatus;
  strategyEnabled: boolean;
};

function ageSeconds(value: string | Date | null, now: number): number | null {
  if (!value) return null;
  const timestamp = value instanceof Date ? value.getTime() : Date.parse(value);
  if (!Number.isFinite(timestamp)) return null;
  return Math.max(0, Math.floor((now - timestamp) / 1000));
}

function ageLabel(seconds: number | null): string {
  if (seconds === null) return "等待首个有效快照";
  if (seconds < 60) return `${seconds}秒前`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`;
  return `${Math.floor(seconds / 3600)}小时前`;
}

function cacheLabel(cached: boolean, age: number | null): string {
  if (age === null) return "尚未采集";
  return `${cached ? "复用缓存" : "刚刚采集"} · ${ageLabel(age)}`;
}

function candidateScanLabel(strategy: QuantStrategyDashboard): string {
  if (strategy.candidate_scan_state === "pending") return "后台预热中 · 首次扫描不会阻塞页面";
  if (strategy.candidate_scan_state === "failed") return "扫描失败 · 等待下一次重试";
  return cacheLabel(strategy.candidate_scan_cached, strategy.candidate_scan_age_seconds);
}

function candidateScanElapsed(strategy: QuantStrategyDashboard, now: number): number | null {
  if (strategy.candidate_scan_state !== "pending" || !strategy.candidate_scan_started_at) return null;
  const started = Date.parse(strategy.candidate_scan_started_at);
  if (!Number.isFinite(started)) return null;
  return Math.max(0, Math.floor((now - started) / 1000));
}

function candidateScanDeterminate(strategy: QuantStrategyDashboard): { processed: number; total: number; percent: number } | null {
  if (strategy.candidate_scan_state !== "pending" || strategy.candidate_scan_phase !== "computing_factors") return null;
  const processed = strategy.candidate_scan_processed;
  const total = strategy.candidate_scan_total;
  if (processed === null || total === null || total <= 0 || processed < 0) return null;
  const safeProcessed = Math.min(processed, total);
  return { processed: safeProcessed, total, percent: Math.round((safeProcessed / total) * 100) };
}

function statusLabel(status: QuantLiveStatus): string {
  return {
    loading: "正在连接",
    live: "实时更新",
    delayed: "保留最后有效值",
    paused: "页面隐藏已暂停",
    error: "数据不可用",
  }[status];
}

export function QuantLiveStatusBar({
  board,
  boardStatus,
  boardLastSuccessAt,
  latestTick,
  tickStatus,
  strategy,
  strategyStatus,
  strategyEnabled,
}: Props) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const strategyAge = useMemo(() => {
    if (!strategy) return null;
    const elapsed = ageSeconds(strategy.generated_at, now) ?? 0;
    return strategy.data_age_seconds + elapsed;
  }, [now, strategy]);
  const scanElapsed = strategy ? candidateScanElapsed(strategy, now) : null;
  const scanDeterminate = strategy ? candidateScanDeterminate(strategy) : null;
  const effectiveStrategyStatus = strategy?.refresh_mode === "stale"
    ? "delayed"
    : strategyStatus;
  const activeStatuses = strategyEnabled
    ? [boardStatus, tickStatus, effectiveStrategyStatus]
    : [boardStatus, tickStatus];
  const overall = activeStatuses.includes("paused")
    ? "paused"
    : activeStatuses.some((value) => value === "error" || value === "delayed")
      ? "delayed"
      : activeStatuses.some((value) => value === "loading")
        ? "loading"
        : "live";

  return <section className={`quant-live-status ${overall}`} role="region" aria-label="量化实时数据状态">
    <header>
      <span><RadioTower size={15} />{statusLabel(overall)}</span>
      <small>真实数据分层刷新 · 页面隐藏时自动暂停</small>
    </header>
    <div>
      <article className={tickStatus}>
        <span><Clock3 size={13} />TICK 1秒</span>
        <b>{statusLabel(tickStatus)}</b>
        <small>{ageLabel(ageSeconds(latestTick?.observed_at ?? null, now))} · {latestTick?.source ?? "本地盘中归档"}</small>
      </article>
      <article className={effectiveStrategyStatus}>
        <span><Database size={13} />市场策略 5秒</span>
        <b>{!strategyEnabled ? "未启用" : strategy ? {
          live: "行情实时",
          delayed: "行情延迟",
          postclose: "盘后快照",
          stale: "行情陈旧",
        }[strategy.refresh_mode] : statusLabel(strategyStatus)}</b>
        <small>{strategyEnabled ? `${ageLabel(strategyAge)} · ${strategy?.sources.slice(0, 2).join(" + ") || "本地通达信市场截面"}` : "当前页面未配置策略接口"}</small>
        {strategyEnabled && strategy && <>
          <em className="quant-cache-detail">候选扫描：{candidateScanLabel(strategy)} · 触发证据：{cacheLabel(strategy.trigger_evidence_cached, strategy.trigger_evidence_age_seconds)}{strategy.candidate_scan_error ? ` · ${strategy.candidate_scan_error}` : ""}</em>
          {scanElapsed !== null && <div className="quant-scan-progress-wrap">
            <div
              className={`quant-scan-progress${scanDeterminate ? " determinate" : ""}`}
              role="progressbar"
              aria-label="候选扫描后台预热"
              aria-busy="true"
              aria-valuemin={scanDeterminate ? 0 : undefined}
              aria-valuemax={scanDeterminate ? 100 : undefined}
              aria-valuenow={scanDeterminate?.percent}
            >
              <i style={scanDeterminate ? { width: `${scanDeterminate.percent}%` } : undefined} />
            </div>
            <small>{scanDeterminate
              ? `因子扫描 ${scanDeterminate.processed}/${scanDeterminate.total} · ${scanDeterminate.percent}%`
              : `已运行 ${scanElapsed} 秒 · 进度由本地扫描决定`}</small>
          </div>}
        </>}
      </article>
      <article className={boardStatus}>
        <span><Database size={13} />候选池 30秒</span>
        <b>{statusLabel(boardStatus)}</b>
        <small>{ageLabel(ageSeconds(boardLastSuccessAt, now))} · {board?.as_of ?? "等待规则池"}</small>
      </article>
    </div>
  </section>;
}
