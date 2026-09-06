import { BookOpenCheck, CalendarClock, Database, ExternalLink, Landmark, Plus, Users } from "lucide-react";

import type { ResearchEnrichmentEvidence, ResearchReportEvidence } from "./types";

function number(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function amount(value: string | null | undefined): string {
  const parsed = number(value);
  if (parsed === null) return "--";
  if (Math.abs(parsed) >= 100_000_000) return `${(parsed / 100_000_000).toFixed(2)}亿`;
  if (Math.abs(parsed) >= 10_000) return `${(parsed / 10_000).toFixed(1)}万`;
  return parsed.toFixed(2);
}

function median(values: Array<number | null>): number | null {
  const sorted = values.filter((item): item is number => item !== null).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function ReportRows({ reports, empty }: { reports: ResearchReportEvidence[]; empty: string }) {
  if (!reports.length) return <p className="research-enrichment-empty">{empty}</p>;
  return <div className="research-report-rows">{reports.slice(0, 8).map((report) => <article key={report.report_id}>
    <time>{report.publish_date}</time>
    <span><b>{report.title}</b><small>{report.organization} · {report.rating ?? "未提供评级"} · {report.industry ?? "行业未标注"}</small></span>
    <strong>{report.eps_next_year === null ? "EPS --" : `明年 EPS ${Number(report.eps_next_year).toFixed(2)}`}</strong>
    {report.pdf_url && <a href={report.pdf_url} target="_blank" rel="noreferrer" aria-label={`查看研报：${report.title}`}><ExternalLink size={14} /></a>}
  </article>)}</div>;
}

export function ResearchEnrichmentPanel({
  value,
  currentSymbol,
  onAddPeer,
}: {
  value?: ResearchEnrichmentEvidence;
  currentSymbol?: string;
  onAddPeer?: (symbol: string, name: string) => void;
}) {
  const enrichment = value ?? {
    status: "unavailable" as const, observed_at: null, stock_reports: [], industry_reports: [],
    industry_name: null, industry_code: null, industry_board_code: null, peer_candidates: [],
    unlocks: [], margin: [], holders: [], sources: [], reasons: ["后台研究扩展数据尚未返回"],
  };
  const nextEps = median(enrichment.stock_reports.map((item) => number(item.eps_next_year)));
  const today = new Date().toISOString().slice(0, 10);
  const upcomingUnlocks = enrichment.unlocks.filter((item) => item.free_date >= today);
  const latestMargin = enrichment.margin[0];
  const latestHolder = enrichment.holders[0];
  const holderChange = number(latestHolder?.change_ratio_percent);
  const peerCandidates = (enrichment.peer_candidates ?? [])
    .filter((item) => item.symbol !== currentSymbol)
    .slice(0, 8);
  const latestIndustryReport = [...enrichment.industry_reports]
    .sort((left, right) => right.publish_date.localeCompare(left.publish_date))[0];
  return <section className="research-card research-enrichment" aria-label="机构研究与筹码证据">
    <header className="research-card-header">
      <div><p className="eyebrow">INSTITUTION / CAPITAL EVIDENCE</p><h2>机构研究与筹码证据</h2></div>
      <span className={`research-status ${enrichment.status}`}>{enrichment.status === "ready" ? "缓存已更新" : enrichment.status === "partial" ? "部分字段可用" : "后台采集中"}</span>
    </header>
    <div className="research-enrichment-metrics">
      <article><BookOpenCheck /><span>个股研报</span><strong>{enrichment.stock_reports.length || "--"}</strong><small>东财公开研报</small></article>
      <article><Database /><span>行业研报</span><strong>{enrichment.industry_reports.length || "--"}</strong><small>同行业公开研报</small></article>
      <article><Landmark /><span>明年 EPS 中位</span><strong>{nextEps === null ? "--" : nextEps.toFixed(2)}</strong><small>{nextEps === null ? "一致预期待补" : `${enrichment.stock_reports.filter((item) => item.eps_next_year !== null).length} 份预测样本`}</small></article>
      <article><CalendarClock /><span>未来解禁</span><strong>{upcomingUnlocks.length || "--"}</strong><small>{upcomingUnlocks[0] ? `${upcomingUnlocks[0].free_date} · ${upcomingUnlocks[0].ratio_percent ?? "--"}%` : "未来记录待核验"}</small></article>
      <article><Landmark /><span>融资余额</span><strong>{amount(latestMargin?.financing_balance)}</strong><small>{latestMargin?.trade_date ?? "交易日待补"}</small></article>
      <article className={holderChange !== null && holderChange < 0 ? "up" : holderChange !== null && holderChange > 0 ? "down" : "flat"}><Users /><span>股东户数变化</span><strong>{holderChange === null ? "--" : `${holderChange > 0 ? "+" : ""}${holderChange.toFixed(2)}%`}</strong><small>{latestHolder?.period ?? "报告期待补"} · 户数 {amount(latestHolder?.holder_count)}</small></article>
    </div>
    <section className="research-peer-suggestions" aria-label="系统自动筛选同行">
      <header>
        <div><p className="eyebrow">VERIFIED INDUSTRY PEERS</p><h3>系统自动筛选同行</h3></div>
        <div className="research-peer-tags">
          <span>{enrichment.shenwan_industry?.name ?? "申万行业待核验"}</span>
          <span>{enrichment.shenwan_industry?.code ?? "申万行业代码待核验"}</span>
          <small>{enrichment.shenwan_industry ? `申万${enrichment.shenwan_industry.level} · ${enrichment.shenwan_industry.version}` : "来源分类仅作映射证据"}</small>
          <span>{enrichment.industry_reports.length ? `${enrichment.industry_reports.length} 份行业研报` : "行业研报待补"}</span>
        </div>
      </header>
    <p className="research-peer-method">同行只取已映射到同一申万行业的真实成分股，并按总市值排序；其它来源分类仅作为映射证据，不直接作为行业口径。{latestIndustryReport ? ` 最近行业证据：${latestIndustryReport.publish_date}《${latestIndustryReport.title}》。` : " 当前尚无行业研报缓存。"}</p>
      {peerCandidates.length ? <div className="research-peer-grid">{peerCandidates.map((peer) => {
        const change = number(peer.change_percent);
        return <article key={peer.symbol}>
          <div><strong>{peer.name}</strong><span>{peer.symbol}</span></div>
          <dl><div><dt>现价</dt><dd>{number(peer.price)?.toFixed(2) ?? "--"}</dd></div><div><dt>涨跌</dt><dd className={change === null ? "flat" : change >= 0 ? "up" : "down"}>{change === null ? "--" : `${change > 0 ? "+" : ""}${change.toFixed(2)}%`}</dd></div><div><dt>PE / PB</dt><dd>{number(peer.pe_ttm)?.toFixed(1) ?? "--"} / {number(peer.pb)?.toFixed(1) ?? "--"}</dd></div><div><dt>市值</dt><dd>{number(peer.market_cap_yi)?.toFixed(1) ?? "--"}亿</dd></div></dl>
          {onAddPeer && <button type="button" aria-label={`将${peer.name}加入同行比较`} onClick={() => onAddPeer(peer.symbol, peer.name)}><Plus size={14} />加入对比</button>}
        </article>;
      })}</div> : <p className="research-enrichment-empty">同一行业板块成分股缓存尚未建立，不自动猜测同行。</p>}
    </section>
    <div className="research-enrichment-columns">
      <section><h3>个股研报与 EPS 预测</h3><ReportRows reports={enrichment.stock_reports} empty="个股研报缓存尚未建立" /></section>
      <section><h3>行业研报</h3><ReportRows reports={enrichment.industry_reports} empty="行业代码或行业研报尚未取得" /></section>
    </div>
    <footer>来源：{enrichment.sources.join(" / ") || "后台低频采集任务"} · {enrichment.observed_at ? `缓存时间 ${new Date(enrichment.observed_at).toLocaleString("zh-CN", { hour12: false })}` : "首次进入后后台采集，页面不等待远程接口"}{enrichment.reasons.length ? ` · ${enrichment.reasons.join("；")}` : ""}</footer>
  </section>;
}
