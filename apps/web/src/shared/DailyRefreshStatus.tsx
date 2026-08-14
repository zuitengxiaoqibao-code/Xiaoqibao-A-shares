import { CheckCircle2, Database, LoaderCircle, Radio, TriangleAlert } from "lucide-react";

import type { LoadProgress, LoadProgressMode, LoadStage } from "./fetchJsonWithProgress";
import "./dailyRefreshStatus.css";

type Props = {
  label: string;
  cachedAt?: string | null;
  loading: boolean;
  completion?: "live" | "partial";
  progress?: LoadProgress | null;
  error?: string | null;
  updatedAt?: string | null;
};

function formatTime(value: string | null | undefined): string {
  if (!value) return "无缓存";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

const stageNames: Record<LoadStage, string> = {
  connecting: "服务连接",
  receiving: "数据接收",
  parsing: "数据校验与解析",
  complete: "结果刷新",
};

const progressModeNames: Record<LoadProgressMode, string> = {
  estimated: "阶段估算",
  measured: "真实字节",
  verified: "已核验节点",
};

function progressMode(progress: LoadProgress | null | undefined): LoadProgressMode {
  if (progress?.mode) return progress.mode;
  if (progress?.stage === "receiving") return "measured";
  if (progress?.stage === "parsing" || progress?.stage === "complete") return "verified";
  return "estimated";
}

function formatElapsed(elapsedMs: number | undefined): string | null {
  if (elapsedMs === undefined || elapsedMs < 0) return null;
  return `已等待 ${(elapsedMs / 1_000).toFixed(1)} 秒`;
}

export function DailyRefreshStatus({ label, cachedAt, loading, completion = "live", progress, error, updatedAt }: Props) {
  const percent = Math.max(1, Math.min(100, progress?.percent ?? (loading ? 1 : 100)));
  const mode = progressMode(progress);
  const elapsed = formatElapsed(progress?.elapsedMs);
  const partial = !error && !loading && Boolean(updatedAt) && completion === "partial";
  const status = error ? "error" : loading ? "loading" : partial ? "partial" : "ready";
  const monitoring = !error && !loading && !partial && Boolean(updatedAt);
  const title = error
    ? cachedAt ? "最新数据更新失败，继续显示当日缓存" : "最新数据加载失败"
    : loading
      ? cachedAt ? "正在载入最新数据，当前先展示当日缓存" : "正在载入最新数据"
      : partial ? "已加载最新可用数据"
      : monitoring ? "已加载实时最新数据" : "已加载当日缓存";
  const timestamp = monitoring || partial
    ? `最新数据时间：${formatTime(updatedAt)}`
    : cachedAt ? `缓存时间：${formatTime(cachedAt)}` : "尚无当日缓存";

  return <section className={`daily-refresh-status ${status} ${monitoring ? "monitoring" : ""}`} role="status" aria-label={`${label}数据刷新状态`} data-monitoring={monitoring ? "live" : partial ? "partial" : "idle"}>
    <div className="daily-refresh-heading">
      {error ? <TriangleAlert size={17} /> : loading ? <LoaderCircle size={17} className="spin" /> : monitoring ? <Radio size={17} className="live-pulse" /> : updatedAt ? <CheckCircle2 size={17} /> : <Database size={17} />}
      <div><strong>{title}</strong><span>{timestamp}</span></div>
      <b className="daily-refresh-percent">{error ? "失败" : loading ? `${percent}%` : partial ? "待补齐" : monitoring ? "LIVE" : "缓存"}</b>
    </div>
    {loading && <div className="daily-refresh-progress-row">
      <span className={`daily-refresh-progress-mode ${mode}`}>{progressModeNames[mode]}</span>
      {elapsed && <small>{elapsed}</small>}
      <div className="daily-refresh-progress-track active" role="progressbar" aria-valuemin={1} aria-valuemax={100} aria-valuenow={percent} aria-label={`${label}最新数据加载进度`} data-progress-mode={mode}><span style={{ width: `${percent}%` }} /><i aria-hidden="true" /></div>
    </div>}
    {monitoring && <div className="daily-refresh-progress-track complete" role="progressbar" aria-valuemin={1} aria-valuemax={100} aria-valuenow={100} aria-label={`${label}实时监控状态`}><span /></div>}
    {error ? <div className="daily-refresh-failure">
      <span><b>失败环节：</b>{stageNames[progress?.stage ?? "connecting"]}</span>
      <span><b>失败对象：</b>{label}最新数据</span>
      <span><b>原因：</b>{error}</span>
      {progress?.detail && <small>失败前状态：{progress.detail}</small>}
    </div> : <div className="daily-refresh-detail"><span>{partial ? "核心行情已更新，扩展数据仍待补齐" : monitoring ? "当前状态：实时监控中..." : progress?.detail ?? `数据范围：${label}`}</span></div>}
  </section>;
}
