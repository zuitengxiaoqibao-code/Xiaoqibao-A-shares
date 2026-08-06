import { useMemo, useState } from "react";

import type { LatestTipCategory, LatestTipItem } from "./types";


const categories: Array<"全部" | LatestTipCategory> = [
  "全部", "公告与合同", "业绩预告", "资金与融资", "交易异动", "风险提醒", "其他",
];

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

export function LatestTipEvidencePanel({ items, source, observedAt }: { items: LatestTipItem[]; source: string; observedAt: string | null }) {
  const [activeCategory, setActiveCategory] = useState<"全部" | LatestTipCategory>("全部");
  const filtered = activeCategory === "全部" ? items : items.filter((item) => item.category === activeCategory);
  const summary = useMemo(() => {
    const risk = items.filter((item) => item.tone === "risk").length;
    const positive = items.filter((item) => item.tone === "positive").length;
    const latestDate = items.flatMap((item) => item.date ? [item.date] : []).sort().reverse()[0] ?? "--";
    return { risk, positive, latestDate };
  }, [items]);

  return <section className="research-card evidence-timeline" aria-label="催化与最新提示">
    <div className="research-card-header">
      <div><p className="eyebrow">F10 EVENT LEDGER</p><h2>催化与最新提示</h2></div>
      <span className={`research-status ${items.length ? "ready" : "unavailable"}`}>{source}</span>
    </div>
    {items.length === 0 ? <div className="evidence-empty">
      <strong>通达信 F10 未返回最新提示</strong>
      <span>当前没有可核验事件，不使用推测内容填补。</span>
    </div> : <>
      <div className="evidence-summary" aria-label="最新提示摘要">
        <div><span>证据摘要</span><strong>已识别 {items.length} 项事件</strong></div>
        <div><span>明确催化</span><strong>{summary.positive} 项</strong></div>
        <div><span>风险提醒</span><strong>{summary.risk} 项</strong></div>
        <div><span>最近日期</span><strong>{summary.latestDate}</strong></div>
        <div><span>观察时间</span><strong>{formatObservedAt(observedAt)}</strong></div>
      </div>
      <div className="evidence-filters" aria-label="最新提示分类">
        {categories.map((category) => <button
          key={category}
          type="button"
          className={activeCategory === category ? "active" : ""}
          aria-pressed={activeCategory === category}
          onClick={() => setActiveCategory(category)}
        >{category}</button>)}
      </div>
      <div className="evidence-events">
        {filtered.map((item) => <article className={`evidence-event ${item.tone}`} key={item.id}>
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
      {filtered.length === 0 && <div className="evidence-empty compact"><strong>该分类暂无事件</strong><span>请选择其他分类查看。</span></div>}
    </>}
  </section>;
}
