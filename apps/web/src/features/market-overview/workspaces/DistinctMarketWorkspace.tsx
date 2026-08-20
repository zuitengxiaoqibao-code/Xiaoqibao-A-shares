import { Clock3, Database, HelpCircle, Radio, ShieldAlert } from "lucide-react";
import { useMemo } from "react";

import type { MarketOverviewResponse } from "../types";
import type { MarketIntervalReviewLoader } from "../types";
import { featureDisplayLabel } from "../featureCatalog";
import { IntervalStatisticsWorkspace } from "../IntervalStatisticsWorkspace";
import { WorkspaceBlockView } from "./WorkspaceBlocks";
import { WorkspaceInsightDashboard } from "./WorkspaceInsightDashboard";
import { getWorkspaceDefinition } from "./workspaceRegistry";
import { buildWorkspaceInsights } from "./workspaceInsights";
import { buildWorkspaceMarketModel } from "./workspaceSelectors";

function fullTime(value: string | null): string {
  if (!value) return "--";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
    hour12: false, timeZone: "Asia/Shanghai",
  }).format(new Date(value));
}

function sourceName(value: string): string {
  if (["tdx-local-rpc", "tdx-local-realtime"].includes(value)) return "本地通达信";
  if (value === "market-db") return "本地历史库（已核验来源）";
  return value === "unavailable" ? "行情源不可用" : value;
}

function historySourceName(value: string | undefined): string {
  if (!value) return "未接入";
  if (value === "market-db") return "本地历史库（通达信/百度回填链路）";
  if (value === "tdx-local-day") return "通达信本地日线文件";
  return value;
}

function calendarLagDays(liveDate: string | null, historyDate: string | null): number | null {
  if (!liveDate || !historyDate) return null;
  const live = Date.parse(`${liveDate}T00:00:00Z`);
  const history = Date.parse(`${historyDate}T00:00:00Z`);
  if (!Number.isFinite(live) || !Number.isFinite(history) || history >= live) return 0;
  return Math.floor((live - history) / 86_400_000);
}

function qualityLabel(quality: MarketOverviewResponse["market_data"]["quality"]): string {
  switch (quality) {
    case "ready": return "实时证据已连接";
    case "partial": return "部分证据可用";
    case "stale": return "使用缓存待更新";
    case "unavailable": return "当前行情不可用";
  }
}

function workspaceStatus(marketData: MarketOverviewResponse["market_data"]): { label: string; detail: string } {
  if (marketData.freshness === "previous_close") {
    return { label: "上一交易日收盘快照", detail: "上一交易日收盘快照 · 等待开盘" };
  }
  if (marketData.freshness === "final") {
    return { label: "当日收盘最终快照", detail: "收盘数据已确认 · 等待下一交易日" };
  }
  if (marketData.freshness === "stale") {
    return { label: "历史快照待更新", detail: "数据时间较旧 · 不生成模拟值" };
  }
  return {
    label: qualityLabel(marketData.quality),
    detail: marketData.quality === "ready" ? "5 秒刷新 · 不生成模拟值" : "保留真实状态 · 不生成模拟值",
  };
}

export function DistinctMarketWorkspace({ feature, data, onOpenAShare, onOpenCompanyResearch, onOpenQuantAnalysis, loadIntervalReview }: {
  feature: string;
  data: MarketOverviewResponse;
  onOpenAShare?: (symbol: string) => void;
  onOpenCompanyResearch?: (symbol: string) => void;
  onOpenQuantAnalysis?: (symbol: string) => void;
  loadIntervalReview?: MarketIntervalReviewLoader;
}) {
  const definition = getWorkspaceDefinition(feature);
  const displayLabel = featureDisplayLabel(feature);
  const model = useMemo(() => buildWorkspaceMarketModel(data), [data]);
  const insights = useMemo(() => buildWorkspaceInsights(feature, data, model), [data, feature, model]);
  const coverage = data.market_data.universe_count > 0
    ? data.market_data.quote_count / data.market_data.universe_count * 100
    : null;
  const status = workspaceStatus(data.market_data);
  const dataScope = data.data_scope;
  const queryDate = data.as_of || null;
  const liveDate = data.market_data.observed_at?.slice(0, 10) || data.as_of || null;
  const historyDate = data.review?.latest_trade_date ?? null;
  const latestAvailableHistoryDate = data.review?.latest_available_trade_date ?? historyDate;
  const historyDateFragmented = Boolean(
    data.review?.warnings.includes("history_dates_fragmented")
    || data.review?.warnings.includes("history_latest_outlier")
    || (latestAvailableHistoryDate && historyDate && latestAvailableHistoryDate !== historyDate),
  );
  const historyCoverage = data.review?.latest_trade_date_coverage_percent
    ?? (data.review && data.review.universe_count > 0
      ? (data.review.history_ready_count / data.review.universe_count * 100).toFixed(1)
      : null);
  const latestAvailableCount = data.review?.latest_available_trade_date_count ?? null;
  const historyLag = calendarLagDays(liveDate, historyDate);
  const historyState = historyDate === null
    ? "unavailable"
    : data.review?.refresh_required || data.review?.quality === "stale" || data.review?.quality === "partial" || (historyLag !== null && historyLag > 0)
      ? "stale"
      : "ready";

  return <section
    className={`distinct-workspace layout-${definition.layout}`}
    aria-label={`${definition.label}专属工作区`}
    data-layout={definition.layout}
  >
    <header className="distinct-workspace-hero">
      <div><span>{definition.family} / DISTINCT WORKSPACE</span><h2>{displayLabel}</h2><p>{definition.question}</p></div>
      <aside data-quality={data.market_data.quality}><Radio size={17} /><div><small>工作区状态</small><b>{status.label}</b><span>{status.detail}</span></div></aside>
    </header>

    <section className="distinct-provenance" aria-label={`${definition.label}数据来源`}>
      <div><Database size={16} /><span><small>行情主源</small><b>{sourceName(data.market_data.source)}</b></span></div>
      <div><Clock3 size={16} /><span><small>快照时间</small><b>{fullTime(data.market_data.observed_at)}</b></span></div>
      <div><Radio size={16} /><span><small>{dataScope?.market_aggregate === "full_a_share_market" ? "A 股全市场聚合" : "行情覆盖"}</small><b>{dataScope?.market_aggregate === "full_a_share_market"
        ? `${dataScope.market_quote_count.toLocaleString("zh-CN")} / ${dataScope.market_universe_count.toLocaleString("zh-CN")} 只行情`
        : coverage === null ? "--" : `${coverage.toFixed(1)}% · ${data.market_data.quote_count} / ${data.market_data.universe_count}`}</b></span></div>
      {dataScope?.stock_sample === "representative" && <div><Database size={16} /><span><small>代表股票范围</small><b>{dataScope.stock_sample_count.toLocaleString("zh-CN")} 只代表股票样本</b></span></div>}
      {dataScope && dataScope.sector_sample !== "none" && <div><Database size={16} /><span><small>板块样本范围</small><b>{dataScope.sector_sample_count.toLocaleString("zh-CN")} 个{dataScope.sector_sample === "strong_sector" ? "强势板块" : "资讯关联板块"}样本</b></span></div>}
      <div><ShieldAlert size={16} /><span><small>本页严格边界</small><b>{definition.requiredEvidence.join(" · ")}</b></span></div>
    </section>

    <section className="distinct-history-freshness" data-state={historyState} aria-label="历史日线新鲜度">
      <div><small>查询日期</small><strong>{queryDate ?? "--"}</strong></div>
      <div><small>实时行情日期</small><strong>实时行情 {liveDate ?? "--"}</strong></div>
      <div><small>历史日线最新交易日</small><strong>{historyDate ?? "--"}</strong></div>
      <div><small>快照生成时间</small><strong>{fullTime(data.review?.observed_at ?? null)}</strong></div>
      {historyDateFragmented && <>
        <div><small>主导历史交易日</small><strong>{historyDate ?? "--"}</strong></div>
        <div><small>零散最新记录</small><strong>最新零散记录 {latestAvailableHistoryDate ?? "--"}{latestAvailableCount !== null ? `（仅 ${latestAvailableCount} 只）` : ""}</strong></div>
      </>}
      <div className="distinct-history-freshness-status">
        <b>{historyState === "stale" ? "历史日线待补齐" : historyState === "ready" ? "历史日线与行情日期一致" : "历史日线不可用"}</b>
        <span>{historyDateFragmented
          ? `当前复盘使用覆盖率 ${historyCoverage ?? "--"}% 的主导交易日 ${historyDate ?? "--"}；更晚日期仅有少量零散记录，不纳入全市场复盘。${data.review?.refresh_reason ?? "历史日线覆盖日期分散，不能代表查询日期全市场"}。来源：${historySourceName(data.review?.source)}`
          : historyState === "stale" ? `当前复盘使用 ${historyDate} 的真实历史数据，落后 ${historyLag ?? "未知"} 个日历日；${data.review?.refresh_reason ?? "历史日线待补齐"}；补齐前不把实时快照当作历史序列。来源：${historySourceName(data.review?.source)}`
            : historyState === "ready" ? `历史筛选与当前交易日对齐。来源：${historySourceName(data.review?.source)}`
              : "没有可验证的历史交易日，相关历史筛选保持不可用。"}</span>
      </div>
    </section>

    {feature === "区间统计" && loadIntervalReview
      ? <IntervalStatisticsWorkspace
        asOf={data.review?.latest_trade_date ?? data.as_of}
        load={loadIntervalReview}
        onOpenAShare={onOpenAShare}
        onOpenCompanyResearch={onOpenCompanyResearch}
        onOpenQuantAnalysis={onOpenQuantAnalysis}
      />
      : <>
        <WorkspaceInsightDashboard feature={displayLabel} insights={insights} actions={{ onOpenAShare, onOpenCompanyResearch, onOpenQuantAnalysis }} />

        <div className="distinct-block-grid">
          {definition.blocks.map((block) => <WorkspaceBlockView
            key={`${block.kind}-${block.variant}`}
            block={block}
            definition={definition}
            data={data}
            model={model}
            onOpenAShare={onOpenAShare}
            onOpenCompanyResearch={onOpenCompanyResearch}
            onOpenQuantAnalysis={onOpenQuantAnalysis}
          />)}
        </div>
      </>}

    <footer className="distinct-guidance">
      <section><HelpCircle size={18} /><div><b>新手阅读顺序</b><p>{definition.beginnerGuide}</p></div></section>
      <section><ShieldAlert size={18} /><div><b>数据与结论边界</b><p>{definition.truthBoundary}</p></div></section>
    </footer>
  </section>;
}
