import { AlertTriangle, RefreshCw } from "lucide-react";

export type SectionRefreshStateKind = "ready" | "refreshing" | "stale" | "partial" | "unavailable" | "error";

type Props = {
  state: Exclude<SectionRefreshStateKind, "ready" | "refreshing">;
  phase: string;
  error?: string | null;
  onRetry: () => void;
};

const copy: Record<Props["state"], { label: string; role: "status" | "alert" }> = {
  stale: { label: "保留上一次真实数据", role: "status" },
  partial: { label: "部分数据可用", role: "status" },
  unavailable: { label: "当前区块暂无可用数据", role: "alert" },
  error: { label: "当前区块加载失败", role: "alert" },
};

export function SectionRefreshState({ state, phase, error, onRetry }: Props) {
  const content = copy[state];
  return <div className={`section-refresh-state state-${state}`} role={content.role} aria-live="polite">
    <AlertTriangle size={15} aria-hidden="true" />
    <span className="section-refresh-copy">
      <b>{content.label}</b>
      <small>{phase}{error ? ` · ${error}` : ""}</small>
    </span>
    <button type="button" onClick={onRetry} aria-label="重试本区块"><RefreshCw size={13} />重试本区块</button>
  </div>;
}
