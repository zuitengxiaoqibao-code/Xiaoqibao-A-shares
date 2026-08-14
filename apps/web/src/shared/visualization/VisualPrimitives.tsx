import type { ReactNode } from "react";

import { chartToneColor } from "./chartTheme";
import type { EvidenceState, EvidenceStatus, MetricItem, MetricTone, RankItem } from "./types";
import { freshnessDetail, freshnessLabel } from "../evidence/freshnessCopy";

import "./visualization.css";

function classes(...values: Array<string | undefined | false>): string {
  return values.filter(Boolean).join(" ");
}

function valueLabel(value: number | string | null, unavailable = "数据不可用"): string {
  if (value === null || value === undefined || (typeof value === "number" && !Number.isFinite(value))) return unavailable;
  return typeof value === "number" ? String(value) : value;
}

function formatObservedAt(value: string | null): string {
  if (!value) return "时间未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatCoverage(value: number | null): string {
  return value !== null && Number.isFinite(value) ? `覆盖 ${Math.round(value)}%` : "覆盖未知";
}

export function DataStateNotice({ state, title, detail, onRetry }: {
  state: EvidenceState;
  title?: string;
  detail?: string;
  onRetry?: () => void;
}) {
  const heading = title ?? freshnessLabel(state.status);
  const description = detail ?? freshnessDetail(state.status);
  return (
    <div className="viz-state-notice" data-status={state.status} role="status" aria-label={heading}>
      <span className="viz-state-dot" aria-hidden="true" />
      <div className="viz-state-copy">
        <strong>{heading}</strong>
        <span>{freshnessLabel(state.status)} · {description}</span>
        <small>来源：{state.source} · 观测时间：{formatObservedAt(state.observedAt)} · {formatCoverage(state.coverage)}</small>
        {state.warnings.length > 0 && <small className="viz-state-warning">{state.warnings.join("；")}</small>}
      </div>
      {onRetry && <button type="button" onClick={onRetry} aria-label={`重试${heading}`}>重试</button>}
    </div>
  );
}

export function ChartPanel({ title, subtitle, state, ariaLabel, children }: {
  title: string;
  subtitle?: string;
  state?: EvidenceState;
  ariaLabel: string;
  children: ReactNode;
}) {
  return (
    <section className="viz-chart-panel" aria-label={ariaLabel}>
      <header className="viz-chart-panel-header">
        <div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>
        {state && <EvidenceBadge status={state.status} />}
      </header>
      {state && state.status !== "ready" && <DataStateNotice state={state} title={`${title}：${freshnessLabel(state.status)}`} />}
      <div className="viz-chart-panel-content">{children}</div>
    </section>
  );
}

export function MetricBand({ items }: { items: MetricItem[] }) {
  return (
    <section className="viz-metric-band" aria-label="关键指标">
      {items.map((item) => {
        const tone = item.tone ?? "neutral";
        const value = valueLabel(item.value);
        return <article key={item.label} className={classes("viz-metric", `tone-${tone}`)} data-tone={tone}>
          <span>{item.label}</span><strong>{value}</strong>{item.detail && <small>{item.detail}</small>}
        </article>;
      })}
    </section>
  );
}

export function GaugeRow({ label, value, max = 100, tone, detail, state }: {
  label: string;
  value: number | null;
  max?: number;
  tone: MetricTone;
  detail?: string;
  state?: EvidenceState;
}) {
  const valid = value !== null && Number.isFinite(value);
  const safeMax = Number.isFinite(max) && max > 0 ? max : 100;
  const percent = valid ? Math.max(0, Math.min(100, (value / safeMax) * 100)) : 0;
  const text = valid ? String(value) : "数据不可用";
  return <div className={classes("viz-gauge-row", `tone-${tone}`)} data-state={state?.status}>
    <div className="viz-gauge-heading"><span>{label}</span><strong>{text}</strong></div>
    <div className="viz-gauge-track" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={safeMax} aria-valuenow={valid ? value : undefined} aria-valuetext={text}>
      {valid && <i style={{ width: `${percent}%`, backgroundColor: chartToneColor(tone) }} />}
    </div>
    {(detail || state?.source) && <small>{detail ?? `来源：${state?.source}`}</small>}
  </div>;
}

export function RankBarList({ items, state }: { items: RankItem[]; state?: EvidenceState }) {
  const max = Math.max(...items.flatMap((item) => item.value !== null && Number.isFinite(item.value) ? [Math.abs(item.value)] : []), 1);
  return <div className="viz-rank-list" aria-label="排序条形图">
    {state && state.status !== "ready" && <DataStateNotice state={state} title="排序数据状态" />}
    {items.map((item) => {
      const numericValue = item.value;
      const valid = numericValue !== null && Number.isFinite(numericValue);
      const width = valid ? Math.max(0, Math.min(100, (Math.abs(numericValue) / max) * 100)) : 0;
      return <div className="viz-rank-item" key={item.label}>
        <div className="viz-rank-heading"><span>{item.label}</span><strong>{valid ? String(numericValue) : "--"}</strong></div>
        <div className="viz-rank-track" aria-hidden="true">{valid && <i style={{ width: `${width}%` }} />}</div>
        {item.detail && <small>{item.detail}</small>}
      </div>;
    })}
  </div>;
}

export function EvidenceBadge({ status, label }: { status: EvidenceStatus; label?: string }) {
  return <span className="viz-evidence-badge" data-status={status} role="status">{label ?? freshnessLabel(status)}</span>;
}
