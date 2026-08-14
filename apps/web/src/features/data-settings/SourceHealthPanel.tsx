import { Activity, AlertTriangle, ChevronDown, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { friendlyError } from "../../shared/friendlyError";
import type { SourceHealthItem, SourceHealthLoader, SourceHealthResponse } from "./types";

type Props = { load: SourceHealthLoader };

const statusLabel: Record<SourceHealthItem["status"], string> = {
  ready: "就绪",
  degraded: "降级",
  unavailable: "不可用",
};

function valueOrDash(value: number | string | null | undefined): string {
  return value === null || value === undefined || value === "" ? "--" : String(value);
}

function observedLabel(value: string | null): string {
  if (!value) return "最近成功：--";
  return `最近成功：${new Date(value).toLocaleString("zh-CN", { hour12: false })}`;
}

export function SourceHealthPanel({ load }: Props) {
  const [response, setResponse] = useState<SourceHealthResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);
  const mounted = useRef(true);

  const refresh = useCallback(() => {
    setBusy(true);
    setError("");
    void load().then((value) => {
      if (!mounted.current) return;
      setResponse(value);
    }).catch((reason) => {
      if (mounted.current) setError(friendlyError(reason, "数据源健康"));
    }).finally(() => {
      if (mounted.current) setBusy(false);
    });
  }, [load]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (expanded) refresh();
  }, [expanded, refresh]);

  const readyCount = response?.sources.filter((item) => item.status === "ready").length ?? 0;
  const degradedCount = response?.sources.filter((item) => item.status === "degraded").length ?? 0;
  const unavailableCount = response?.sources.filter((item) => item.status === "unavailable").length ?? 0;
  const summaryStatus = response
    ? `${response.sources.length} 个来源 · 就绪 ${readyCount} · 降级 ${degradedCount} · 不可用 ${unavailableCount}`
    : "展开后读取最近真实调用记录";

  return <section
    className="source-health-panel"
    aria-label="数据源健康"
    data-expanded={expanded ? "true" : "false"}
  >
    <button
      type="button"
      className="source-health-summary"
      aria-label={expanded ? "收起数据源健康" : "展开数据源健康"}
      aria-expanded={expanded}
      onClick={() => setExpanded((value) => !value)}
    >
      <span className="source-health-summary-title"><Activity size={15} /><strong>数据源健康</strong></span>
      <span className="source-health-summary-status">{summaryStatus}</span>
      <ChevronDown size={17} aria-hidden="true" />
    </button>
    {expanded && <div className="source-health-content">
      <header className="source-health-heading">
        <div>
          <small>按最近 {response?.window_size ?? 20} 次真实调用汇总；不代表字段一定完整</small>
        </div>
        <div>
          {response && <time dateTime={response.generated_at}>更新于 {new Date(response.generated_at).toLocaleString("zh-CN", { hour12: false })}</time>}
          <button type="button" className="settings-action secondary source-health-refresh" onClick={refresh} disabled={busy}>
            <RefreshCw size={14} className={busy ? "spin" : undefined} />刷新数据源健康
          </button>
        </div>
      </header>

      {error && <p className="source-health-warning" role="alert"><AlertTriangle size={14} />{error}（保留上一次成功结果）</p>}
      {!response && busy && <p className="source-health-empty" role="status">正在读取数据源调用记录...</p>}
      {response?.sources.length === 0 && !busy && <p className="source-health-empty">当前窗口暂无数据源调用记录</p>}
      {response && response.sources.length > 0 && <div className="source-health-list">
        {response.sources.map((item) => <article className={`source-health-card ${item.status}`} key={`${item.source}-${item.operation}-${item.target}`}>
          <header className="source-health-card-heading">
            <b>{item.source} · {item.operation}</b>
            <span>{statusLabel[item.status]}</span>
          </header>
          <small>目标：{item.target}</small>
          <p>成功率 {item.success_rate.toFixed(2)}% · 最近延迟 {item.latest_latency_ms}ms · 平均 {item.average_latency_ms}ms</p>
          <p>{observedLabel(item.last_success_at)} · 最新交易日：{valueOrDash(item.latest_trade_date)}</p>
          <p>字段数：{valueOrDash(item.field_count)} · 行数：{valueOrDash(item.row_count)}{item.validation ? ` · ${item.validation}` : ""}</p>
          {item.last_error_code && <p className="source-health-warning">最近错误：{item.last_error_code}</p>}
        </article>)}
      </div>}
    </div>}
  </section>;
}
