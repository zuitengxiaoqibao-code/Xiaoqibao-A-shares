import { Clock3, Database, HelpCircle, Radio, ShieldAlert } from "lucide-react";
import { useMemo } from "react";

import type { MarketOverviewResponse } from "../types";
import type { MarketIntervalReviewLoader } from "../types";
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
  return value === "unavailable" ? "行情源不可用" : value;
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

export function DistinctMarketWorkspace({ feature, data, onOpenAShare, loadIntervalReview }: {
  feature: string;
  data: MarketOverviewResponse;
  onOpenAShare?: (symbol: string) => void;
  loadIntervalReview?: MarketIntervalReviewLoader;
}) {
  const definition = getWorkspaceDefinition(feature);
  const model = useMemo(() => buildWorkspaceMarketModel(data), [data]);
  const insights = useMemo(() => buildWorkspaceInsights(feature, data, model), [data, feature, model]);
  const coverage = data.market_data.universe_count > 0
    ? data.market_data.quote_count / data.market_data.universe_count * 100
    : null;
  const status = workspaceStatus(data.market_data);

  return <section
    className={`distinct-workspace layout-${definition.layout}`}
    aria-label={`${definition.label}专属工作区`}
    data-layout={definition.layout}
  >
    <header className="distinct-workspace-hero">
      <div><span>{definition.family} / DISTINCT WORKSPACE</span><h2>{definition.label}</h2><p>{definition.question}</p></div>
      <aside data-quality={data.market_data.quality}><Radio size={17} /><div><small>工作区状态</small><b>{status.label}</b><span>{status.detail}</span></div></aside>
    </header>

    <section className="distinct-provenance" aria-label={`${definition.label}数据来源`}>
      <div><Database size={16} /><span><small>行情主源</small><b>{sourceName(data.market_data.source)}</b></span></div>
      <div><Clock3 size={16} /><span><small>快照时间</small><b>{fullTime(data.market_data.observed_at)}</b></span></div>
      <div><Radio size={16} /><span><small>行情覆盖</small><b>{coverage === null ? "--" : `${coverage.toFixed(1)}% · ${data.market_data.quote_count} / ${data.market_data.universe_count}`}</b></span></div>
      <div><ShieldAlert size={16} /><span><small>本页严格边界</small><b>{definition.requiredEvidence.join(" · ")}</b></span></div>
    </section>

    {feature === "区间统计" && loadIntervalReview
      ? <IntervalStatisticsWorkspace
        asOf={data.review?.latest_trade_date ?? data.as_of}
        load={loadIntervalReview}
        onOpenAShare={onOpenAShare}
      />
      : <>
        <WorkspaceInsightDashboard feature={definition.label} insights={insights} />

        <div className="distinct-block-grid">
          {definition.blocks.map((block) => <WorkspaceBlockView
            key={`${block.kind}-${block.variant}`}
            block={block}
            definition={definition}
            data={data}
            model={model}
            onOpenAShare={onOpenAShare}
          />)}
        </div>
      </>}

    <footer className="distinct-guidance">
      <section><HelpCircle size={18} /><div><b>新手阅读顺序</b><p>{definition.beginnerGuide}</p></div></section>
      <section><ShieldAlert size={18} /><div><b>数据与结论边界</b><p>{definition.truthBoundary}</p></div></section>
    </footer>
  </section>;
}
