import { Clock3, Database, RefreshCw, ShieldCheck } from "lucide-react";
import { compactFreshnessLabel } from "./freshnessCopy";


type Props = {
  status: "ready" | "partial" | "unavailable" | "stale" | "error";
  tradeDate?: string | null;
  observedAt?: string | null;
  generatedAt?: string | null;
  sourceCount?: number | null;
  sampleCount?: number | null;
  refreshState?: "ready" | "pending" | "failed" | "paused";
  limitations?: string[];
};

const refreshLabels = { ready: "最新数据已载入", pending: "后台刷新中", failed: "刷新失败，保留旧值", paused: "刷新已暂停" };

function time(value: string | null | undefined): string {
  if (!value) return "--";
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) ? parsed.toLocaleString("zh-CN", { hour12: false }) : "--";
}

export function DataWatermarkStrip({ status, tradeDate = null, observedAt = null, generatedAt = null, sourceCount = null, sampleCount = null, refreshState = "ready", limitations = [] }: Props) {
  return <section className="data-watermark-strip" data-status={status} aria-label="数据证据水印">
    <span><ShieldCheck size={14} /><b>{compactFreshnessLabel(status)}</b></span>
    <span><Database size={14} />交易日 <b>{tradeDate ?? "--"}</b></span>
    <span><Clock3 size={14} />观测 <b>{time(observedAt)}</b></span>
    <span>生成 <b>{time(generatedAt)}</b></span>
    <span>{sourceCount === null ? "来源数不可用" : `${sourceCount} 个来源`}</span>
    <span>{sampleCount === null ? "样本数不可用" : `${sampleCount} 条样本`}</span>
    <span><RefreshCw size={13} className={refreshState === "pending" ? "spin" : ""} />{refreshLabels[refreshState]}</span>
    {limitations.slice(0, 3).map((item) => <em key={item}>{item}</em>)}
  </section>;
}
