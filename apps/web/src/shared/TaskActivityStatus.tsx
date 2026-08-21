import { Activity, AlertTriangle, Bot, CheckCircle2, Clock3, LoaderCircle } from "lucide-react";
import { useSyncExternalStore } from "react";
import { readTaskActivities, subscribeTaskActivity, type TaskActivity } from "./taskActivity";

type AIState = "unconfigured" | "configured_unverified" | "connected" | "connection_failed" | "timeout" | "rate_limited" | "model_not_found";
type Props = { ai?: { configured: boolean; state?: AIState; message?: string } | null };

const aiCopy: Record<AIState, { label: string; tone: string }> = {
  unconfigured: { label: "AI 未配置", tone: "muted" }, configured_unverified: { label: "AI 待验证", tone: "pending" },
  connected: { label: "AI 正常", tone: "ok" }, connection_failed: { label: "AI 异常", tone: "bad" },
  timeout: { label: "AI 超时", tone: "bad" }, rate_limited: { label: "AI 限流", tone: "bad" }, model_not_found: { label: "AI 模型异常", tone: "bad" },
};

function taskTone(task: TaskActivity): string { return task.state === "failed" ? "bad" : task.state === "succeeded" ? "ok" : task.state === "queued" ? "pending" : "running"; }

export function TaskActivityStatus({ ai }: Props) {
  const tasks = useSyncExternalStore(subscribeTaskActivity, readTaskActivities, readTaskActivities);
  const aiView = aiCopy[ai?.state ?? (ai?.configured ? "configured_unverified" : "unconfigured")];
  const active = tasks.filter((task) => task.state === "queued" || task.state === "running").slice(0, 3);
  const failed = tasks.find((task) => task.state === "failed");
  return <section className="task-activity-status" aria-label="系统状态与数据任务">
    <header><span><Activity size={14} /><b>系统状态</b></span><small>{active.length ? `处理中 ${active.length}` : failed ? "有任务异常" : "当前空闲"}</small></header>
    <div className={`task-activity-ai ${aiView.tone}`}><Bot size={14} /><span>{aiView.label}</span><small>{ai?.message ?? "正在读取 AI 配置"}</small></div>
    {active.map((task) => <article className="task-activity-row" key={task.id}>
      <span className={`task-activity-dot ${taskTone(task)}`} />
      <div><b>{task.stage}</b><small>{task.label}{task.detail ? ` · ${task.detail}` : ""}</small></div>
      <strong>{task.percent == null ? <LoaderCircle className="task-activity-spin" size={13} /> : `${Math.max(0, Math.min(100, Math.round(task.percent)))}%`}</strong>
    </article>)}
    {!active.length && failed && <article className="task-activity-row failed"><span className="task-activity-dot bad" /><div><b>{failed.label}失败</b><small>{failed.error ?? failed.stage}</small></div><AlertTriangle size={14} /></article>}
    {!active.length && !failed && <div className="task-activity-idle"><CheckCircle2 size={13} />等待数据任务</div>}
    {tasks.some((task) => task.state === "succeeded" && Date.now() - Date.parse(task.updatedAt) < 30_000) && <div className="task-activity-complete"><Clock3 size={12} />最近任务已完成</div>}
  </section>;
}
