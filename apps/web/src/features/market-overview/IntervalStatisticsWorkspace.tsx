import { AlertTriangle, CalendarDays, LoaderCircle, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { MarketIntervalReviewLoader, MarketIntervalReviewSnapshot, MarketIntervalReviewStock } from "./types";
import { interactiveTargetProps } from "./interactiveTarget";
import { DrilldownMetric, MetricDrilldownPanel, type MetricDrilldownSelection } from "./workspaces/MetricDrilldown";

function shiftDate(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function numberValue(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function signedPercent(value: string | null | undefined): string {
  const parsed = numberValue(value);
  return parsed === null ? "--" : `${parsed > 0 ? "+" : ""}${parsed.toFixed(2)}%`;
}

function tone(value: string | null | undefined): "up" | "down" | "flat" {
  const parsed = numberValue(value);
  return parsed === null || parsed === 0 ? "flat" : parsed > 0 ? "up" : "down";
}

function EmptyInterval({ snapshot, error }: { snapshot: MarketIntervalReviewSnapshot | null; error: string | null }) {
  const reason = error ?? snapshot?.warnings.join(" / ") ?? "区间接口没有返回原因";
  return <div className="interval-empty"><AlertTriangle size={24} /><b>未返回可验证的区间样本</b><p>{reason}</p><small>不会用当前快照或成交额代理历史区间收益。</small></div>;
}

function Distribution({ rows }: { rows: MarketIntervalReviewStock[] }) {
  const values = rows.map((row) => numberValue(row.return_percent)).filter((value): value is number => value !== null);
  const bins = [
    ["跌幅 <= -10%", values.filter((value) => value <= -10).length, "down"],
    ["跌幅 -10% ~ 0", values.filter((value) => value > -10 && value < 0).length, "down"],
    ["涨幅 0% ~ 10%", values.filter((value) => value >= 0 && value < 10).length, "flat"],
    ["涨幅 10% ~ 30%", values.filter((value) => value >= 10 && value < 30).length, "up"],
    ["涨幅 >= 30%", values.filter((value) => value >= 30).length, "up"],
  ] as const;
  const max = Math.max(1, ...bins.map((item) => item[1]));
  return <section className="interval-distribution"><header><b>区间收益分布</b><span>{values.length} 只有效收益</span></header>{bins.map(([label, value, itemTone]) => <div key={label}><span>{label}</span><i className={itemTone} style={{ width: `${value / max * 100}%` }} /><strong>{value}</strong></div>)}<footer>收益 = 区间结束收盘 / 区间起始收盘 - 1；上涨红色，回撤绿色。</footer></section>;
}

function IntervalTable({ rows, onOpenAShare }: { rows: MarketIntervalReviewStock[]; onOpenAShare?: (symbol: string) => void }) {
  return <div className="interval-table-scroll"><table className="distinct-table interval-table"><thead><tr><th>代码 / 名称</th><th>起始收盘</th><th>结束收盘</th><th>区间收益</th><th>区间振幅</th><th>区间成交额</th></tr></thead><tbody>{rows.slice(0, 80).map((row) => <tr key={row.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(row.symbol) : undefined, `查看 ${row.symbol} ${row.name}`)}><td><span>{row.symbol}{onOpenAShare ? <button type="button" onClick={(event) => { event.stopPropagation(); onOpenAShare(row.symbol); }}>{row.name}</button> : <b>{row.name}</b>}</span></td><td>{row.start_close}</td><td>{row.end_close}</td><td className={tone(row.return_percent)}>{signedPercent(row.return_percent)}</td><td>{signedPercent(row.amplitude_percent)}</td><td>{row.amount_yi}亿</td></tr>)}</tbody></table></div>;
}

export function IntervalStatisticsWorkspace({ asOf, load, onOpenAShare, onOpenCompanyResearch, onOpenQuantAnalysis }: {
  asOf: string;
  load: MarketIntervalReviewLoader;
  onOpenAShare?: (symbol: string) => void;
  onOpenCompanyResearch?: (symbol: string) => void;
  onOpenQuantAnalysis?: (symbol: string) => void;
}) {
  const [startDate, setStartDate] = useState(() => shiftDate(asOf, -28));
  const [endDate, setEndDate] = useState(asOf);
  const [query, setQuery] = useState({ start: shiftDate(asOf, -28), end: asOf });
  const [snapshot, setSnapshot] = useState<MarketIntervalReviewSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selection, setSelection] = useState<MetricDrilldownSelection | null>(null);

  const refresh = useCallback(async (start: string, end: string, signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await load(start, end, signal);
      if (!signal.aborted) setSnapshot(result);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      if (!signal.aborted) setError(reason instanceof Error ? reason.message : "区间统计数据暂不可用");
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [load]);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(query.start, query.end, controller.signal);
    return () => controller.abort();
  }, [query, refresh]);

  const rows = snapshot?.rows ?? [];
  const topGainers = useMemo(() => rows.filter((row) => (numberValue(row.return_percent) ?? 0) > 0).slice(0, 5), [rows]);
  const topLosers = useMemo(() => [...rows].filter((row) => (numberValue(row.return_percent) ?? 0) < 0).sort((a, b) => (numberValue(a.return_percent) ?? 0) - (numberValue(b.return_percent) ?? 0)).slice(0, 5), [rows]);
  const gainers = useMemo(() => rows.filter((row) => (numberValue(row.return_percent) ?? 0) > 0), [rows]);
  const losers = useMemo(() => rows.filter((row) => (numberValue(row.return_percent) ?? 0) < 0), [rows]);
  const drilldownStock = (row: MarketIntervalReviewStock, reason: string) => ({ symbol: row.symbol, name: row.name?.trim() || "名称待补齐", reason, value: signedPercent(row.return_percent) });
  const summaryItems: MetricDrilldownSelection[] = [
    { label: "有效样本", value: snapshot?.valid_count ?? rows.length, source: "真实区间日线", stocks: rows.map((row) => drilldownStock(row, "严格具备区间起止收盘")) },
    { label: "平均收益", value: rows.length ? `${(rows.reduce((sum, row) => sum + (numberValue(row.return_percent) ?? 0), 0) / rows.length).toFixed(2)}%` : "--", source: "逐股简单平均", unavailableReason: "平均收益是聚合值；请使用区间上涨、区间下跌或下方明细表查看成员。" },
    { label: "区间上涨", value: gainers.length, source: "区间收益 > 0", stocks: gainers.map((row) => drilldownStock(row, "区间收益大于 0")) },
    { label: "区间下跌", value: losers.length, source: "区间收益 < 0", stocks: losers.map((row) => drilldownStock(row, "区间收益小于 0")) },
    { label: "最大振幅", value: rows.length ? `${Math.max(...rows.map((row) => numberValue(row.amplitude_percent) ?? 0)).toFixed(2)}%` : "--", source: "逐股区间振幅", stocks: rows.length ? rows.filter((row) => numberValue(row.amplitude_percent) === Math.max(...rows.map((item) => numberValue(item.amplitude_percent) ?? 0))).map((row) => drilldownStock(row, `区间振幅 ${signedPercent(row.amplitude_percent)}`)) : [] },
  ];

  return <section className="interval-statistics-workspace">
    <header className="interval-toolbar"><div><CalendarDays size={18} /><span><b>真实区间统计</b><small>选择日期后读取本地通达信日线，不复用实时快照</small></span></div><form onSubmit={(event) => { event.preventDefault(); if (startDate < endDate) setQuery({ start: startDate, end: endDate }); }}><label>起始日<input type="date" value={startDate} max={endDate} onChange={(event) => setStartDate(event.target.value)} /></label><label>结束日<input type="date" value={endDate} min={startDate} max={asOf} onChange={(event) => setEndDate(event.target.value)} /></label><button type="submit" disabled={loading || startDate >= endDate}><RefreshCw size={14} className={loading ? "spinning" : ""} />计算区间</button></form></header>
    <div className="interval-status" data-state={loading ? "loading" : error ? "error" : snapshot?.quality ?? "unavailable"}><LoaderCircle size={15} className={loading ? "spinning" : ""} /><span>{loading ? `正在加载 ${query.start} 至 ${query.end} 的日线` : error ? error : snapshot?.start_date && snapshot.end_date ? `已加载真实区间 ${snapshot.start_date} 至 ${snapshot.end_date} · ${snapshot.valid_count}/${snapshot.universe_count} 只` : "等待区间结果"}</span></div>
    {rows.length ? <><div className="interval-summary">{summaryItems.map((item) => <article key={item.label}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><span>{item.label}</span><b className={item.label === "平均收益" ? tone(String(rows.reduce((sum, row) => sum + (numberValue(row.return_percent) ?? 0), 0) / rows.length)) : ""}>{item.value}</b><small>{item.source}</small></DrilldownMetric></article>)}</div>{selection && <MetricDrilldownPanel selection={selection} onClose={() => setSelection(null)} actions={{ onOpenAShare, onOpenCompanyResearch, onOpenQuantAnalysis }} />}<div className="interval-panels"><Distribution rows={rows} /><section className="interval-leaderboard"><header><b>区间强势 / 弱势</b><span>前 5 名</span></header><div><aside><strong><TrendingUp size={15} />强势</strong>{topGainers.map((row) => <p key={row.symbol}>{row.name}<em className="up">{signedPercent(row.return_percent)}</em></p>)}</aside><aside><strong><TrendingDown size={15} />弱势</strong>{topLosers.map((row) => <p key={row.symbol}>{row.name}<em className="down">{signedPercent(row.return_percent)}</em></p>)}</aside></div></section></div><IntervalTable rows={rows} onOpenAShare={onOpenAShare} /></> : <EmptyInterval snapshot={snapshot} error={error} />}
    <footer className="interval-footnote">公式版本 {snapshot?.formula_version ?? "a-share-interval-review-v1"} · 来源 {snapshot?.source ?? "tdx-local-day"} · 不构成投资建议</footer>
  </section>;
}
