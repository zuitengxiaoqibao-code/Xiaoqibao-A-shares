import { useMemo, useState } from "react";

import { presentLatestTip } from "./latestTipPresentation";
import type { LatestTipItem, ResearchEnrichmentEvidence } from "./types";


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

function unlockTimelineItems(unlocks: ResearchEnrichmentEvidence["unlocks"]): LatestTipItem[] {
  return unlocks.map((item) => {
    const ratio = item.ratio_percent === null ? null : Number(item.ratio_percent);
    const highRatio = ratio !== null && Number.isFinite(ratio) && ratio >= 5;
    const shares = item.shares === null ? "数量未提供" : `${(Number(item.shares) / 10000).toFixed(1)}万股`;
    return {
      id: `unlock-${item.free_date}-${item.stock_type ?? "unknown"}`,
      category: "风险提醒",
      title: highRatio ? "高比例限售股解禁" : "限售股解禁事项",
      date: item.free_date,
      tone: highRatio ? "risk" : "neutral",
      summary: `${item.stock_type ?? "限售股份"} · ${shares} · 占比 ${ratio === null || !Number.isFinite(ratio) ? "--" : `${ratio.toFixed(2)}%`}`,
      source: "eastmoney-datacenter",
      observed_at: null,
      raw_text: `解禁日期 ${item.free_date}；股份类型 ${item.stock_type ?? "未提供"}；解禁数量 ${item.shares ?? "未提供"}；解禁比例 ${item.ratio_percent ?? "未提供"}%`,
    };
  });
}

export function LatestTipEvidencePanel({
  items,
  source,
  observedAt,
  unlocks = [],
}: {
  items: LatestTipItem[];
  source: string;
  observedAt: string | null;
  unlocks?: ResearchEnrichmentEvidence["unlocks"];
}) {
  const [showAll, setShowAll] = useState(false);
  const timelineItems = useMemo(() => [...items, ...unlockTimelineItems(unlocks)], [items, unlocks]);
  const summary = useMemo(() => {
    const risk = timelineItems.filter((item) => item.tone === "risk").length;
    const positive = timelineItems.filter((item) => item.tone === "positive").length;
    const latestDate = timelineItems.flatMap((item) => item.date ? [item.date] : []).sort().reverse()[0] ?? "--";
    const sorted = [...timelineItems].sort((left, right) => priority(left) - priority(right) || (right.date ?? "").localeCompare(left.date ?? ""));
    const positiveTitle = sorted.find((item) => item.tone === "positive")?.title;
    const headline = risk > 0
      ? `重点风险：${sorted.find((item) => item.tone === "risk")?.title ?? "存在待核验风险"}。${positiveTitle ? `正向事实：${positiveTitle}。` : "暂无明确正向事实。"}`
      : positive > 0
        ? `正向事实：${positiveTitle ?? `发现 ${positive} 项可核验事件`}。当前未识别明确风险。`
        : "当前事件以中性或待确认为主，暂不强行判断方向。";
    return { risk, positive, latestDate, headline, sorted };
  }, [timelineItems]);
  const visibleItems = showAll ? summary.sorted : summary.sorted.slice(0, 3);
  const remainingCount = Math.max(0, summary.sorted.length - 3);

  return <section className="research-card evidence-timeline" aria-label="催化与最新提示">
    <div className="research-card-header">
      <div><p className="eyebrow">F10 EVENT LEDGER</p><h2>催化与最新提示</h2></div>
      <span className={`research-status ${timelineItems.length ? "ready" : "unavailable"}`}>{unlocks.length ? `${source} + 东财事项` : source}</span>
    </div>
    {timelineItems.length === 0 ? <div className="evidence-empty">
      <strong>当前没有有效事件</strong>
      <span>通达信 F10 未返回可核验的公告、业绩或风险信息。</span>
    </div> : <>
      <div className="evidence-verdict" aria-label="重点结论">
        <div><span>重点结论</span><strong>{summary.headline}</strong></div>
        <p>共 {timelineItems.length} 项有效事件 · 最近日期 {summary.latestDate} · 观察时间 {formatObservedAt(observedAt)}</p>
      </div>
      <div className="evidence-events">
        {visibleItems.map((item) => {
          const presentation = presentLatestTip(item);
          return <article className={`evidence-event ${item.tone}`} key={item.id}>
          <header>
            <div><span className="evidence-date">{item.date ?? "日期未识别"}</span><h3>{item.title}</h3></div>
            <span className={`evidence-tone ${item.tone}`}>{toneLabels[item.tone]}</span>
          </header>
          <div className="evidence-reading">
            <div><span>发生了什么</span><p>{presentation.fact}</p></div>
            <div><span>影响判断</span><p>{presentation.impact}</p></div>
            <div><span>后续观察</span><p>{presentation.watch}</p></div>
          </div>
          <footer><span>{item.category}</span><span>{item.source}</span></footer>
          <details className="evidence-raw">
            <summary>查看原始证据</summary>
            <p>{presentation.rawEvidence}</p>
          </details>
        </article>})}
      </div>
      {remainingCount > 0 && <button type="button" className="evidence-more" onClick={() => setShowAll((current) => !current)}>
        {showAll ? "收起其他事件" : `查看其他 ${remainingCount} 项`}
      </button>}
    </>}
  </section>;
}
