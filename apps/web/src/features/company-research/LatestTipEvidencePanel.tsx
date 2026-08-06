import { useMemo, useState } from "react";

import type { LatestTipItem } from "./types";


const toneLabels = {
  positive: "催化",
  neutral: "中性",
  risk: "风险",
  unknown: "待整理",
} as const;

function formatObservedAt(value: string | null): string {
  if (!value) return "无时间戳";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function priority(item: LatestTipItem): number {
  if (item.tone === "risk") return 0;
  if (item.category === "业绩预告") return 1;
  if (item.category === "公告与合同") return 2;
  return 3;
}

export function LatestTipEvidencePanel({ items, source, observedAt }: { items: LatestTipItem[]; source: string; observedAt: string | null }) {
  const [showAll, setShowAll] = useState(false);
  const summary = useMemo(() => {
    const risk = items.filter((item) => item.tone === "risk").length;
    const positive = items.filter((item) => item.tone === "positive").length;
    const latestDate = items.flatMap((item) => item.date ? [item.date] : []).sort().reverse()[0] ?? "--";
    const sorted = [...items].sort((left, right) => priority(left) - priority(right) || (right.date ?? "").localeCompare(left.date ?? ""));
    const headline = risk > 0
      ? `重点风险：${sorted.find((item) => item.tone === "risk")?.title ?? "存在待核验风险"}。${positive > 0 ? `另有 ${positive} 项明确催化。` : "暂无明确正向催化。"}`
      : positive > 0
        ? `发现 ${positive} 项明确催化，当前未识别明确风险。`
        : "暂无明确正向催化；当前没有可核验风险。";
    return { risk, positive, latestDate, headline, sorted };
  }, [items]);
  const visibleItems = showAll ? summary.sorted : summary.sorted.slice(0, 3);
  const remainingCount = Math.max(0, summary.sorted.length - 3);

  return <section className="research-card evidence-timeline" aria-label="催化与最新提示">
    <div className="research-card-header">
      <div><p className="eyebrow">F10 EVENT LEDGER</p><h2>催化与最新提示</h2></div>
      <span className={`research-status ${items.length ? "ready" : "unavailable"}`}>{source}</span>
    </div>
    {items.length === 0 ? <div className="evidence-empty">
      <strong>当前没有有效事件</strong>
      <span>通达信 F10 未返回可核验的公告、业绩或风险信息。</span>
    </div> : <>
      <div className="evidence-verdict" aria-label="重点结论">
        <div><span>重点结论</span><strong>{summary.headline}</strong></div>
        <p>共 {items.length} 项有效事件 · 最近日期 {summary.latestDate} · 观察时间 {formatObservedAt(observedAt)}</p>
      </div>
      <div className="evidence-events">
        {visibleItems.map((item) => <article className={`evidence-event ${item.tone}`} key={item.id}>
          <header>
            <div><span className="evidence-date">{item.date ?? "日期未识别"}</span><h3>{item.title}</h3></div>
            <span className={`evidence-tone ${item.tone}`}>{toneLabels[item.tone]}</span>
          </header>
          <p>{item.summary}</p>
          <footer><span>{item.category}</span><span>{item.source}</span></footer>
          <details className="evidence-raw">
            <summary>查看原始证据</summary>
            <p>{item.raw_text}</p>
          </details>
        </article>)}
      </div>
      {remainingCount > 0 && <button type="button" className="evidence-more" onClick={() => setShowAll((current) => !current)}>
        {showAll ? "收起其他事件" : `查看其他 ${remainingCount} 项`}
      </button>}
    </>}
  </section>;
}
