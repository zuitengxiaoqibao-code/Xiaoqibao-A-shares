import {
  Activity, AlertTriangle, CalendarDays, CheckCircle2, Database,
  FileSearch, Layers3, Network, ShieldAlert, TrendingUp, XCircle,
} from "lucide-react";
import type { EChartsOption } from "echarts";
import { useState, type CSSProperties, type ReactNode } from "react";

import { QuantChart } from "../../quant-analysis/QuantChart";
import { chartTheme } from "../../../shared/visualization/chartTheme";
import type { MarketOverviewResponse, MarketReviewStock } from "../types";
import { interactiveTargetProps } from "../interactiveTarget";
import type { WorkspaceBlock, WorkspaceDefinition } from "./workspaceTypes";
import { hasDragonTigerEvidence } from "./workspaceEvidence";
import {
  numberValue, signedPercent, stocksForVariant,
  stockNameForSymbol,
  type DerivedSector, type DerivedStock, type WorkspaceMarketModel,
} from "./workspaceSelectors";
import { sectorColor } from "./sectorPalette";
import {
  DrilldownMetric, MetricDrilldownPanel,
  type DrilldownStock, type MetricDrilldownSelection, type StockResearchActions,
} from "./MetricDrilldown";

type BlockProps = {
  block: WorkspaceBlock;
  definition: WorkspaceDefinition;
  data: MarketOverviewResponse;
  model: WorkspaceMarketModel;
  onOpenAShare?: (symbol: string) => void;
  onOpenCompanyResearch?: (symbol: string) => void;
  onOpenQuantAnalysis?: (symbol: string) => void;
};

function timeLabel(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    hour12: false, timeZone: "Asia/Shanghai",
  }).format(new Date(value));
}

function tone(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "flat";
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

function known(value: number | null | undefined): value is number {
  return value !== null && value !== undefined && Number.isFinite(value);
}

function compareDesc(a: number | null, b: number | null): number {
  if (!known(a) && !known(b)) return 0;
  if (!known(a)) return 1;
  if (!known(b)) return -1;
  return b - a;
}

function compareAsc(a: number | null, b: number | null): number {
  if (!known(a) && !known(b)) return 0;
  if (!known(a)) return 1;
  if (!known(b)) return -1;
  return a - b;
}

function stateLabel(stock: DerivedStock): string {
  if (stock.state === "limit_up") return "已封涨停";
  if (stock.state === "broken_limit_up") return "触板未封";
  if (stock.state === "limit_down") return "当前跌停";
  if (stock.closePosition === null) return "数据不足";
  return stock.closePosition >= 75 ? "强收区" : stock.closePosition <= 25 ? "弱收区" : "区间中部";
}

function StockName({ stock, onOpenAShare }: { stock: DerivedStock; onOpenAShare?: (symbol: string) => void }) {
  if (!onOpenAShare) return <b>{stock.name}</b>;
  return <button type="button" aria-label={`查看 ${stock.symbol} ${stock.name}`} onClick={(event) => { event.stopPropagation(); onOpenAShare(stock.symbol); }}>{stock.name}</button>;
}

function reviewStock(item: MarketReviewStock, reason: string): DrilldownStock {
  return {
    symbol: item.symbol,
    name: item.name?.trim() || "名称待补齐",
    reason,
    value: signedPercent(numberValue(item.change_percent)),
  };
}

function derivedStock(stock: DerivedStock, reason: string): DrilldownStock {
  return {
    symbol: stock.symbol,
    name: stock.name?.trim() || "名称待补齐",
    reason,
    value: signedPercent(stock.change),
  };
}

function useMetricDrilldown() {
  return useState<MetricDrilldownSelection | null>(null);
}

function DrilldownRegion({ selection, setSelection, actions }: {
  selection: MetricDrilldownSelection | null;
  setSelection: (selection: MetricDrilldownSelection | null) => void;
  actions: StockResearchActions;
}) {
  return selection ? <MetricDrilldownPanel selection={selection} onClose={() => setSelection(null)} actions={actions} /> : null;
}

function Empty({ children }: { children: ReactNode }) {
  return <div className="distinct-empty"><FileSearch size={22} /><b>当前没有可验证记录</b><p>{children}</p></div>;
}

function Frame({ block, children }: { block: WorkspaceBlock; children: ReactNode }) {
  return <section className={`distinct-block block-${block.kind} size-${block.size}`} aria-label={block.title} data-variant={block.variant}>
    <header><div><small>{block.kind.replaceAll("-", " / ").toUpperCase()}</small><h3>{block.title}</h3></div><span>{block.variant}</span></header>
    <div className="distinct-block-body">{children}</div>
  </section>;
}

function StockTable({ stocks, onOpenAShare, mode = "default" }: {
  stocks: DerivedStock[];
  onOpenAShare?: (symbol: string) => void;
  mode?: "default" | "auction" | "failure" | "risk";
}) {
  if (!stocks.length) return <Empty>严格筛选后没有记录，页面不会用其他股票凑数。</Empty>;
  return <div className="distinct-table-scroll"><table className="distinct-table">
    <thead><tr><th>股票</th><th>代码</th>{mode === "auction" && <th>开盘缺口</th>}{mode === "failure" && <th>高点回落</th>}
      <th>当前涨跌</th><th>{mode === "risk" ? "风险状态" : "成交额"}</th><th>可验证状态</th></tr></thead>
    <tbody>{stocks.slice(0, 18).map((stock) => <tr key={stock.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(stock.symbol) : undefined, `查看 ${stock.symbol} ${stock.name}`)}>
      <td><StockName stock={stock} onOpenAShare={onOpenAShare} /></td><td>{stock.symbol}</td>
      {mode === "auction" && <td className={tone(stock.gap)}>{signedPercent(stock.gap)}</td>}
      {mode === "failure" && <td className="down">{signedPercent(stock.highPullback)}</td>}
      <td className={tone(stock.change)}>{signedPercent(stock.change)}</td>
      <td>{mode === "risk" ? stateLabel(stock) : stock.amount === null ? "--" : `${stock.amount.toFixed(2)}亿`}</td><td>{stateLabel(stock)}</td>
    </tr>)}</tbody>
  </table></div>;
}

function MarketPulse({ data, model, variant, actions }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  const marketReady = data.status !== "unavailable"
    && data.market_data.quality !== "unavailable"
    && data.market_data.quote_count > 0;
  if (variant === "opening") {
    const stocks = model.stocks.filter((stock) => known(stock.gap) && known(stock.change));
    const gapUp = stocks.filter((stock) => (stock.gap ?? 0) >= 2);
    const gapDown = stocks.filter((stock) => (stock.gap ?? 0) <= -2);
    const continuation = gapUp.filter((stock) => (stock.change ?? 0) >= (stock.gap ?? 0) - 1);
    const failure = gapUp.filter((stock) => (stock.change ?? 0) < (stock.gap ?? 0) - 2);
    const cards: MetricDrilldownSelection[] = [
      { label: "开盘样本", value: marketReady && stocks.length ? stocks.length : "未接入", source: "同时具备昨收、开盘和现价", stocks: stocks.map((stock) => derivedStock(stock, `开盘缺口 ${signedPercent(stock.gap)} · 当前涨跌 ${signedPercent(stock.change)}`)) },
      { label: "高开 >= 2%", value: marketReady && stocks.length ? gapUp.length : "未接入", source: "开盘价相对昨收", stocks: gapUp.map((stock) => derivedStock(stock, `开盘缺口 ${signedPercent(stock.gap)}，达到高开阈值`)) },
      { label: "低开 <= -2%", value: marketReady && stocks.length ? gapDown.length : "未接入", source: "开盘价相对昨收", stocks: gapDown.map((stock) => derivedStock(stock, `开盘缺口 ${signedPercent(stock.gap)}，达到低开阈值`)) },
      { label: "高开延续", value: marketReady && stocks.length ? continuation.length : "未接入", source: "现涨幅 >= 高开幅度 - 1%", stocks: continuation.map((stock) => derivedStock(stock, `高开 ${signedPercent(stock.gap)} 后当前维持 ${signedPercent(stock.change)}`)) },
      { label: "高开回落", value: marketReady && stocks.length ? failure.length : "未接入", source: "现涨幅低于缺口 2 个百分点", stocks: failure.map((stock) => derivedStock(stock, `高开 ${signedPercent(stock.gap)} 后回落至 ${signedPercent(stock.change)}`)) },
      { label: "开盘题材", value: marketReady && model.themes.length ? model.themes.length : "未接入", source: "本地资讯关联题材", unavailableReason: "该数值统计开盘资讯关联的去重题材数量，不对应单一股票筛选；请进入开盘热点查看题材证据。" },
    ];
    return <><div className="distinct-metric-deck">{cards.map((item) => <article key={item.label}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><span>{item.label}</span><b>{item.value}</b><small>{item.source}</small></DrilldownMetric></article>)}</div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
  }
  const breadthReady = marketReady && data.breadth.valid_count > 0;
  const limitReady = marketReady;
  const liquidityReady = marketReady && data.liquidity.total_amount_yi !== null;
  const cards = [
    ["市场情绪", marketReady && data.sentiment.score !== null ? data.sentiment.score : "未接入", marketReady ? data.sentiment.band : "行情主源不可用"],
    ["上涨 / 下跌", breadthReady ? `${data.breadth.rising_count} / ${data.breadth.falling_count}` : "未接入", breadthReady ? `${data.breadth.valid_count} 只有效` : "有效行情不足"],
    ["涨停 / 跌停", limitReady ? `${data.limit_ecology.limit_up_count} / ${data.limit_ecology.limit_down_count}` : "未接入", limitReady ? `炸板 ${data.limit_ecology.broken_limit_up_count}` : "行情主源不可用"],
    ["封板率", limitReady && data.limit_ecology.seal_rate_percent !== null ? `${data.limit_ecology.seal_rate_percent}%` : "未接入", limitReady ? "涨停 / 触板" : "触板样本不可用"],
    ["成交热度", liquidityReady && data.liquidity.relative_amount !== null ? `${data.liquidity.relative_amount}x` : "未接入", liquidityReady ? `${data.liquidity.total_amount_yi}亿` : "成交额不可用"],
    ["市场风格", marketReady && data.regime?.regime ? data.regime.regime : "未接入", marketReady && data.regime ? `系数 ${Number(data.regime.market_coef).toFixed(1)}` : "因子不足"],
  ];
  return <div className="distinct-metric-deck">{cards.map(([label, value, detail]) => <article key={label}><span>{label}</span><b>{value}</b><small>{detail}</small></article>)}</div>;
}

function EventTimeline({ model, variant, onOpenAShare }: { model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const events = [...model.anomalies].sort((a, b) => {
    if (["voice-priority", "alert-priority"].includes(variant)) {
      const priority = { negative: 0, uncertain: 1, positive: 2, neutral: 3 } as const;
      return priority[a.direction] - priority[b.direction] || b.symbols.length - a.symbols.length;
    }
    return new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime();
  });
  if (!events.length) return <Empty>本地异动库当前没有已关联 A 股的事件。</Empty>;
  return <ol className="distinct-timeline">{events.slice(0, 18).map((item) => <li key={item.anomaly_id} className={`direction-${item.direction}`}>
    <time>{timeLabel(item.occurred_at)}</time><i /><div><b>{item.label}</b><p>{item.headline}</p><small>{item.themes.join(" / ") || "未归入题材"}</small><div className="timeline-stock-links">{item.symbols.length ? item.symbols.map((symbol) => { const name = stockNameForSymbol(model, symbol); return onOpenAShare ? <button type="button" key={symbol} aria-label={`查看 ${symbol} ${name}`} onClick={() => onOpenAShare(symbol)}>{name}<small>{symbol}</small></button> : <span key={symbol}>{name}<small>{symbol}</small></span>; }) : <span>未关联股票</span>}</div></div>
  </li>)}</ol>;
}

function NewsWire({ model, variant, onOpenAShare }: { model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const popularSymbols = new Set(stocksForVariant(model, "attention-score").slice(0, 10).map((item) => item.symbol));
  const anomalySymbols = new Set(model.anomalies.flatMap((item) => item.symbols));
  const events = variant === "interpret" ? model.news.filter((item) => item.review_state === "verified" && item.symbols.length > 0 && item.themes.length > 0)
    : ["linked-only", "calendar-detail"].includes(variant) ? model.news.filter((item) => item.symbols.length > 0)
    : variant === "popular-evidence" ? model.news.filter((item) => item.symbols.some((symbol) => popularSymbols.has(symbol)))
    : ["voice-source", "stock-anomaly-news"].includes(variant) ? model.news.filter((item) => item.symbols.some((symbol) => anomalySymbols.has(symbol)))
    : model.news;
  if (!events.length) return <Empty>本地新闻库没有满足本功能关联条件的 A 股资讯。</Empty>;
  return <div className="distinct-news-wire">{events.slice(0, 16).map((item) => <article key={item.event_id}>
    <div><time>{timeLabel(item.occurred_at)}</time><span className={item.review_state === "verified" ? "verified" : "pending"}>{item.review_state}</span></div>
    <h4>{item.headline}</h4>{item.summary && <p>{item.summary}</p>}
    <footer>{item.themes.map((theme) => <span key={theme}>{theme}</span>)}{item.symbols.map((symbol) => {
      const name = stockNameForSymbol(model, symbol);
      return onOpenAShare
        ? <button type="button" key={symbol} aria-label={`查看 ${symbol} ${name}`} onClick={() => onOpenAShare(symbol)}>{name}<small>{symbol}</small></button>
        : <span key={symbol}>{name}<small>{symbol}</small></span>;
    })}<small>{item.source}</small></footer>
  </article>)}</div>;
}

function AuctionGap({ model, variant, onOpenAShare }: { model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const stocks = stocksForVariant(model, variant).filter((stock) => known(stock.gap)).slice(0, 16);
  if (!stocks.length) return <Empty>当前代表股票快照为空，无法计算开盘价相对昨收的缺口。</Empty>;
  const max = Math.max(1, ...stocks.map((stock) => Math.abs(stock.gap ?? 0)));
  return <div className="auction-gap-chart">{stocks.map((stock) => <article key={stock.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(stock.symbol) : undefined, `查看 ${stock.symbol} ${stock.name}`)}>
    <span><StockName stock={stock} onOpenAShare={onOpenAShare} /><small>{stock.symbol}</small></span>
    <div className={tone(stock.gap)}><i style={{ width: `${Math.max(3, Math.abs(stock.gap ?? 0) / max * 100)}%` }} /></div>
    <strong className={tone(stock.gap)}>{signedPercent(stock.gap)}</strong><em>现 {signedPercent(stock.change)}</em>
  </article>)}</div>;
}

function AuctionGates({ model }: { model: WorkspaceMarketModel }) {
  const rows = stocksForVariant(model, "auction-pass").slice(0, 12);
  if (!rows.length) return <Empty>当前没有可计算竞价规则的代表股票。</Empty>;
  return <div className="rule-gate-table"><div className="rule-gate-head"><span>股票</span><span>缺口 -1%~4%</span><span>现价确认</span><span>成交可用</span><span>结论</span></div>
    {rows.map((stock) => {
      const gapPass = stock.gap !== null && stock.gap >= -1 && stock.gap <= 4;
      const confirmPass = stock.gap !== null && stock.change !== null && stock.closePosition !== null && stock.change >= stock.gap - 1 && stock.closePosition >= 50;
      const amountPass = stock.amount !== null && stock.amount > 0;
      const pass = gapPass && confirmPass && amountPass;
      return <div key={stock.symbol}><b>{stock.name}<small>{stock.symbol}</small></b><span>{gapPass ? <CheckCircle2 /> : <XCircle />}</span><span>{confirmPass ? <CheckCircle2 /> : <XCircle />}</span><span>{amountPass ? <CheckCircle2 /> : <XCircle />}</span><strong className={pass ? "pass" : "blocked"}>{pass ? "观察" : "阻断"}</strong></div>;
    })}
  </div>;
}

function StockMatrix({ model, variant, onOpenAShare }: { model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const stocks = stocksForVariant(model, variant).slice(0, 18);
  if (!stocks.length) return <Empty>该矩阵所需的严格样本当前为空。</Empty>;
  return <div className="stock-signal-matrix">{stocks.map((stock) => <article key={stock.symbol} className={tone(stock.change)} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(stock.symbol) : undefined, `查看 ${stock.symbol} ${stock.name}`)}>
    <header><StockName stock={stock} onOpenAShare={onOpenAShare} /><span>{stock.symbol}</span></header>
    <strong>{signedPercent(stock.change)}</strong><div><span>缺口 {signedPercent(stock.gap)}</span><span>振幅 {optionalValue(stock.amplitude, "%")}</span></div>
    <footer>{stock.themes.slice(0, 2).join(" / ") || stateLabel(stock)}</footer>
  </article>)}</div>;
}

function SectorHeatmap({ model, variant }: { model: WorkspaceMarketModel; variant: string }) {
  const eventThemes = new Set(model.anomalies.flatMap((item) => item.themes));
  const sectors = variant === "down-sector" ? [...model.sectors].filter((item) => known(item.change) && item.change < 0).sort((a, b) => compareAsc(a.change, b.change))
    : ["limit-count", "limit-cluster", "review-sector"].includes(variant) ? [...model.sectors].filter((item) => item.limit_up_count > 0 && known(item.limitDensityPercent)).sort((a, b) => b.limit_up_count - a.limit_up_count || compareDesc(a.limitDensityPercent, b.limitDensityPercent))
    : variant === "amount-context" ? [...model.sectors].filter((item) => known(item.amount)).sort((a, b) => compareDesc(a.amount, b.amount))
    : variant === "event-sector" ? [...model.sectors].filter((item) => eventThemes.has(item.name))
    : model.sectors;
  if (!sectors.length) return <Empty>本地板块快照没有满足本功能严格条件的记录。</Empty>;
  return <div className="sector-heatmap">{sectors.slice(0, 20).map((sector) => <article key={sector.sector_id} className={tone(sector.change)} style={{ "--strength": `${Math.max(18, sector.strengthScore ?? 18)}%` } as CSSProperties}>
    <b>{sector.name}</b><strong>{signedPercent(sector.change)}</strong><span>广度 {optionalValue(sector.breadthPercent, "%")}</span><small>涨停 {sector.limit_up_count} · {optionalValue(sector.amount, "亿")}</small>
  </article>)}</div>;
}

function SectorQuadrant({ model, variant }: { model: WorkspaceMarketModel; variant: string }) {
  const yLabel = variant === "wind" ? "涨停扩散" : variant === "race" ? "涨幅" : "强度";
  const yValue = (sector: DerivedSector): number | null => variant === "wind" ? sector.limitDensityPercent : variant === "race" ? sector.change : sector.strengthScore;
  const sectors = model.sectors.filter((sector) => known(yValue(sector)) && known(sector.breadthPercent));
  if (!sectors.length) return <Empty>缺少板块广度与{yLabel}字段，无法生成四象限。</Empty>;
  const breadthValues = sectors.map((sector) => sector.breadthPercent as number);
  const breadthRange = Math.max(...breadthValues) - Math.min(...breadthValues);
  if (sectors.length < 3 || breadthRange < 8) {
    const ranked = [...sectors].sort((a, b) => compareDesc(yValue(a), yValue(b))).slice(0, 16);
    const maxMagnitude = Math.max(1, ...ranked.map((sector) => Math.abs(yValue(sector) ?? 0)));
    const formatValue = (value: number) => variant === "race" ? signedPercent(value) : `${value.toFixed(1)}${variant === "wind" ? "%" : ""}`;
    return <div className="sector-ranked-bars" data-testid="sector-ranked-bars">
      <header><div><b>{yLabel}排序</b><span>样本上涨占比缺少区分度，改用强度排序</span></div><small>横轴原始口径：样本上涨占比</small></header>
      {ranked.map((sector) => {
        const value = yValue(sector) as number;
        return <article key={sector.sector_id}><b>{sector.name}</b><div className={tone(sector.change)}><i style={{ width: `${Math.max(4, Math.abs(value) / maxMagnitude * 100)}%` }} /></div><strong className={tone(sector.change)}>{formatValue(value)}</strong><small>样本上涨 {sector.breadthPercent?.toFixed(1)}% · {sector.rising_count + sector.falling_count} 只有效</small></article>;
      })}
    </div>;
  }
  const yValues = sectors.map((sector) => yValue(sector) as number);
  const yRange = Math.max(...yValues) - Math.min(...yValues);
  const median = (values: number[]) => {
    const ordered = [...values].sort((left, right) => left - right);
    const middle = Math.floor(ordered.length / 2);
    return ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
  };
  const breadthThreshold = median(breadthValues);
  const changeValues = sectors.map((sector) => sector.change).filter(known);
  const useChangeFallback = variant === "strength-breadth" && yRange < 8 && changeValues.length > 0;
  const decisionValue = (sector: DerivedSector) => useChangeFallback ? sector.change : yValue(sector);
  const decisionValues = sectors.map(decisionValue).filter(known);
  const decisionThreshold = median(decisionValues);
  const decisionLabel = useChangeFallback || variant === "race" ? "涨幅" : variant === "wind" ? "涨停密度" : "强度";
  const definitions = variant === "wind" ? [
    { key: "main", title: "涨停扩散", summary: "密度高 · 广度高", strong: true, broad: true },
    { key: "core", title: "龙头集中", summary: "密度高 · 广度低", strong: true, broad: false },
    { key: "broad", title: "跟涨扩散", summary: "密度低 · 广度高", strong: false, broad: true },
    { key: "weak", title: "风口退潮", summary: "密度低 · 广度低", strong: false, broad: false },
  ] : variant === "race" ? [
    { key: "main", title: "赛道领涨", summary: "涨幅强 · 广度高", strong: true, broad: true },
    { key: "core", title: "局部抱团", summary: "涨幅强 · 广度低", strong: true, broad: false },
    { key: "broad", title: "广度修复", summary: "涨幅弱 · 广度高", strong: false, broad: true },
    { key: "weak", title: "赛道退潮", summary: "涨幅弱 · 广度低", strong: false, broad: false },
  ] : [
    { key: "main", title: "主线扩散", summary: "强度高 · 广度高", strong: true, broad: true },
    { key: "core", title: "核心抱团", summary: "强度高 · 广度低", strong: true, broad: false },
    { key: "broad", title: "普涨偏弱", summary: "强度低 · 广度高", strong: false, broad: true },
    { key: "weak", title: "弱势收缩", summary: "强度低 · 广度低", strong: false, broad: false },
  ];
  const grouped = definitions.map((definition) => ({
    ...definition,
    sectors: sectors.filter((sector) => {
      const strong = (decisionValue(sector) ?? Number.NEGATIVE_INFINITY) >= decisionThreshold;
      const broad = (sector.breadthPercent ?? Number.NEGATIVE_INFINITY) >= breadthThreshold;
      return strong === definition.strong && broad === definition.broad;
    }).sort((left, right) => compareDesc(decisionValue(left), decisionValue(right)) || compareDesc(left.breadthPercent, right.breadthPercent)),
  }));
  const formatDecision = (value: number | null) => value === null ? "--" : decisionLabel === "涨幅" ? signedPercent(value) : `${value.toFixed(1)}${decisionLabel === "涨停密度" ? "%" : ""}`;
  const reason = useChangeFallback ? "综合强度封顶、缺少区分度，已改用真实涨幅" : `按${decisionLabel}与上涨广度的样本中位数分组`;
  return <div className="sector-decision-shell" data-testid="sector-decision-quadrants">
    <header><div><b>{variant === "wind" ? "风口扩散矩阵" : variant === "race" ? "赛道强弱矩阵" : "板块决策四象限"}</b><span>{reason}</span></div><small>分界：{decisionLabel} {formatDecision(decisionThreshold)} · 广度 {breadthThreshold.toFixed(1)}%</small></header>
    <div className="sector-decision-grid">{grouped.map((group) => <section className={`sector-decision-quadrant ${group.key}`} key={group.key}>
      <header><div><b>{group.title}</b><span>{group.summary}</span></div><strong>{group.sectors.length}</strong></header>
      <div>{group.sectors.length ? group.sectors.slice(0, 8).map((sector) => <article key={sector.sector_id}>
        <div><b>{sector.name}</b><strong className={tone(sector.change)}>{signedPercent(sector.change)}</strong></div>
        <p><span>广度 {sector.breadthPercent?.toFixed(1)}%</span><span>涨停 {sector.limit_up_count}</span>{variant === "wind" && <span>涨停密度 {sector.limitDensityPercent?.toFixed(1)}%</span>}<span>样本 {sector.rising_count + sector.falling_count}</span></p>
      </article>) : <p className="sector-decision-empty">当前没有落入该区域的板块</p>}</div>
    </section>)}</div>
    <footer>{variant === "wind" ? "判读：优先核验涨停扩散区，龙头集中区需防止后排缺乏跟随。" : variant === "race" ? "判读：赛道领涨表示涨幅和广度共振；局部抱团只代表少数核心强。" : "判读：优先观察主线扩散；核心抱团说明强度集中在少数股票。"}</footer>
  </div>;
}

function SectorMembers({ data, model, variant, onOpenAShare }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const sector = variant === "limit-followers" || variant === "leader-sector"
    ? [...model.sectors].sort((a, b) => b.limit_up_count - a.limit_up_count || compareDesc(a.strengthScore, b.strengthScore))[0]
    : model.sectors[0];
  const members = sector ? data.sector_stocks[sector.sector_id] ?? [] : [];
  if (!sector || !members.length) return <Empty>最强板块当前没有已验证成分股明细。</Empty>;
  return <div className="sector-member-list"><header><b>{sector.name}</b><span>{members.length} 条已加载</span></header>{members.slice(0, 18).map((stock) => <article key={stock.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(stock.symbol) : undefined, `查看 ${stock.symbol} ${stock.name}`)}>
    <span>{onOpenAShare ? <button type="button" aria-label={`查看 ${stock.symbol} ${stock.name}`} onClick={(event) => { event.stopPropagation(); onOpenAShare(stock.symbol); }}>{stock.name}</button> : <b>{stock.name}</b>}<small>{stock.symbol}</small></span>
    <strong className={tone(numberValue(stock.change_percent))}>{signedPercent(numberValue(stock.change_percent))}</strong><em>{stock.position}</em>
  </article>)}</div>;
}

function SectorLimitBoard({ data, model, onOpenAShare }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; onOpenAShare?: (symbol: string) => void }) {
  const sector = [...model.sectors]
    .filter((item) => item.limit_up_count > 0)
    .sort((a, b) => b.limit_up_count - a.limit_up_count || compareDesc(a.strengthScore, b.strengthScore))[0];
  const stateBySymbol = new Map(model.stocks.map((stock) => [stock.symbol, stock.state]));
  const members = sector
    ? (data.sector_stocks[sector.sector_id] ?? []).filter((stock) => stock.first_limit_time !== null || stateBySymbol.get(stock.symbol) === "limit_up")
    : [];
  if (!sector) return <Empty>板块快照中没有涨停扩散板块。</Empty>;
  if (!members.length) return <Empty>{sector.name}没有取得首封时间或严格涨停状态一致的成分股。</Empty>;
  return <div className="sector-limit-board"><header><TrendingUp size={20} /><div><small>涨停扩散领先板块</small><b>{sector.name}</b></div><span>板块涨停 {sector.limit_up_count} 只 · 已验证成员 {members.length} 只</span></header><div className="distinct-table-scroll"><table className="distinct-table"><thead><tr><th>股票</th><th>代码</th><th>涨跌幅</th><th>成交额</th><th>板块位置</th><th>首次涨停</th></tr></thead><tbody>{members.slice(0, 18).map((stock) => <tr key={stock.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(stock.symbol) : undefined, `查看 ${stock.symbol} ${stock.name}`)}><td>{onOpenAShare ? <button type="button" aria-label={`查看 ${stock.symbol} ${stock.name}`} onClick={(event) => { event.stopPropagation(); onOpenAShare(stock.symbol); }}>{stock.name}</button> : <b>{stock.name}</b>}</td><td>{stock.symbol}</td><td className={tone(numberValue(stock.change_percent))}>{signedPercent(numberValue(stock.change_percent))}</td><td>{optionalValue(stock.amount_yi, "亿")}</td><td>{stock.position || "--"}</td><td>{stock.first_limit_time ?? "现价已验证"}</td></tr>)}</tbody></table></div></div>;
}

function ThemeAtlas({ model, variant, onOpenAShare }: { model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const themes = ["anomaly-theme"].includes(variant) ? model.themes.filter((item) => item.anomalyCount > 0).sort((a, b) => b.anomalyCount - a.anomalyCount)
    : ["evidence-growth", "ai-evidence"].includes(variant) ? model.themes.filter((item) => item.evidenceCount >= 2).sort((a, b) => b.evidenceCount - a.evidenceCount)
    : ["broadcast-tags", "industry-docs"].includes(variant) ? model.themes.filter((item) => item.newsCount > 0).sort((a, b) => b.newsCount - a.newsCount)
    : variant === "opening-theme" ? [...model.themes].sort((a, b) => new Date(b.latestAt).getTime() - new Date(a.latestAt).getTime())
    : model.themes;
  if (!themes.length) return <Empty>本地新闻和异动中没有满足本功能条件的可追溯题材。</Empty>;
  return <div className="theme-atlas">{themes.slice(0, 24).map((theme, index) => <article key={theme.name} className={index < 3 ? "hot" : ""}>
    <header><b>{theme.name}</b><strong>{theme.evidenceCount}</strong></header><p className="theme-atlas-stocks">{theme.symbols.length ? theme.symbols.slice(0, 6).map((symbol) => {
      const name = stockNameForSymbol(model, symbol);
      return onOpenAShare
        ? <button type="button" key={symbol} aria-label={`查看 ${symbol} ${name}`} onClick={() => onOpenAShare(symbol)}><b>{name}</b><small>{symbol}</small></button>
        : <span key={symbol}><b>{name}</b><small>{symbol}</small></span>;
    }) : "未关联股票"}</p>
    <footer><span>新闻 {theme.newsCount}</span><span>异动 {theme.anomalyCount}</span><time>{timeLabel(theme.latestAt)}</time></footer>
  </article>)}</div>;
}

function ThemeMatrix({ model, onOpenAShare }: { model: WorkspaceMarketModel; onOpenAShare?: (symbol: string) => void }) {
  const stocks = stocksForVariant(model, "theme-count").filter((item) => item.themes.length > 0).slice(0, 14);
  const themes = model.themes.slice(0, 8);
  if (!stocks.length || !themes.length) return <Empty>当前没有同时具备股票代码与题材标签的证据。</Empty>;
  return <div className="theme-overlap-matrix"><div className="matrix-head"><span>股票</span>{themes.map((theme) => <b key={theme.name}>{theme.name}</b>)}</div>{stocks.map((stock) => <div key={stock.symbol}><span>{onOpenAShare ? <button type="button" aria-label={`查看 ${stock.symbol} ${stock.name}`} onClick={() => onOpenAShare(stock.symbol)}>{stock.name}<small>{stock.symbol}</small></button> : <>{stock.name}<small>{stock.symbol}</small></> }</span>{themes.map((theme) => <i key={theme.name} className={stock.themes.includes(theme.name) ? "hit" : ""}>{stock.themes.includes(theme.name) ? "●" : "·"}</i>)}</div>)}</div>;
}

function LimitEcology({ data, model, variant, actions }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  const marketReady = data.status !== "unavailable" && data.market_data.quote_count > 0;
  const touched = data.limit_ecology.limit_up_count + data.limit_ecology.broken_limit_up_count;
  const failureRate = touched > 0 ? `${(data.limit_ecology.broken_limit_up_count / touched * 100).toFixed(1)}%` : "--";
  const riskBalance = data.limit_ecology.limit_up_count > 0
    ? `${(data.limit_ecology.limit_down_count / data.limit_ecology.limit_up_count).toFixed(2)}x`
    : "--";
  if (!marketReady) return <Empty>行情主源不可用，涨跌停生态暂不计算。</Empty>;
  const meterRows = [
    { key: "sealed", label: "封板", value: data.limit_ecology.limit_up_count, color: "up" },
    { key: "broken", label: "炸板", value: data.limit_ecology.broken_limit_up_count, color: "watch" },
    { key: "down", label: "跌停", value: data.limit_ecology.limit_down_count, color: "down" },
  ] as const;
  const maxCount = Math.max(1, ...meterRows.map((item) => item.value));
  const selections: MetricDrilldownSelection[] = [
    { label: "已封涨停", value: data.limit_ecology.limit_up_count, source: "严格现价状态", stocks: stocksForVariant(model, "strict-limit").map((stock) => derivedStock(stock, "当前价格达到严格涨停状态")), totalLabel: "全市场统计" },
    { label: "触板未封", value: data.limit_ecology.broken_limit_up_count, source: "最高价触板", stocks: stocksForVariant(model, "strict-broken").map((stock) => derivedStock(stock, "最高价触及涨停但当前未封住")), totalLabel: "全市场统计" },
    { label: "当前跌停", value: data.limit_ecology.limit_down_count, source: "风险样本", stocks: stocksForVariant(model, "strict-down").map((stock) => derivedStock(stock, "当前价格达到严格跌停状态")), totalLabel: "全市场统计" },
    { label: variant === "risk-balance" ? "跌停 / 封板" : variant === "seal-failure" ? "炸板占比" : "触板合计", value: variant === "risk-balance" ? riskBalance : variant === "seal-failure" ? failureRate : touched, source: variant === "risk-balance" ? "风险 / 强势" : variant === "seal-failure" ? "炸板 / 触板" : "涨停 + 炸板", unavailableReason: "该数值是市场结构比率或合计；请分别点击已封涨停、触板未封或当前跌停查看逐股明细。" },
    { label: "封板率", value: data.limit_ecology.seal_rate_percent !== null ? `${data.limit_ecology.seal_rate_percent}%` : "--", source: "已封 / 触板", unavailableReason: "封板率是全市场聚合比率；请点击已封涨停或触板未封查看当前已加载的逐股明细。" },
  ];
  return <div className="limit-ecology-deck">
    {selections.map((item, index) => <article key={item.label} className={index === 0 ? "sealed" : index === 1 ? "broken" : index === 2 ? "down" : undefined}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><span>{item.label}</span><b>{item.value}</b><small>{item.source}</small></DrilldownMetric></article>)}
    <div className="limit-ecology-visual" aria-label="涨跌停生态图形化对照">
      <header><b>涨跌停生态对照</b><span>红涨绿跌：红色为上涨/改善，绿色为下跌/风险</span></header>
      {meterRows.map((item) => <div className="limit-ecology-meter" key={item.key} data-testid={`limit-ecology-meter-${item.key}`} aria-label={`${item.label === "封板" ? "已封涨停" : item.label}占触板比例`}>
        <span>{item.label}</span><div className={item.color}><i style={{ width: `${Math.max(0, item.value / maxCount * 100)}%` }} /></div><strong>{item.value}</strong>
      </div>)}
    </div>
    <DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} />
  </div>;
}

function reviewDate(data: MarketOverviewResponse): string {
  return data.review?.latest_trade_date ?? "交易日不可用";
}

function optionalValue(value: string | number | null | undefined, suffix = ""): string {
  if (value === null || value === undefined || value === "") return "--";
  const numeric = typeof value === "number"
    ? value
    : /^[-+]?\d+(?:\.\d+)?$/.test(value.trim()) ? Number(value) : null;
  if (numeric === null || !Number.isFinite(numeric)) return `${value}${suffix}`;
  return `${Number(numeric.toFixed(2))}${suffix}`;
}

function signedYi(value: string | number | null | undefined): string {
  const parsed = numberValue(value);
  return parsed === null ? "--" : `${parsed >= 0 ? "+" : ""}${Number(parsed.toFixed(2))}亿`;
}

function ReviewSummary({ data, variant, actions }: { data: MarketOverviewResponse; variant: string; actions: StockResearchActions }) {
  const review = data.review;
  const [selection, setSelection] = useMetricDrilldown();
  if (!review) return <Empty>本地日线复盘尚未完成首次扫描。</Empty>;
  if (variant === "dragon-tiger" && !hasDragonTigerEvidence(review)) return <Empty>龙虎榜公开接口当前不可用，且本地没有可用的真实缓存。</Empty>;
  const coverage = review.universe_count > 0 ? review.history_ready_count / review.universe_count * 100 : null;
  const boardHeights = review.consecutive_limit_up.map((item) => item.board_count).filter((value): value is number => value !== null && Number.isFinite(value));
  const ladderTop = boardHeights.length ? Math.max(...boardHeights) : null;
  const coverageLabel = optionalValue(coverage, "%");
  const rows: MetricDrilldownSelection[] = variant === "limit-ladder" ? [
    { label: "最高连板", value: ladderTop === null ? "--" : `${ladderTop}板`, source: "连续收盘涨停", stocks: review.consecutive_limit_up.filter((item) => item.board_count === ladderTop).map((item) => reviewStock(item, `真实日线验证 ${ladderTop ?? "--"} 板`)) },
    { label: "连板股票", value: review.consecutive_limit_up.length, source: "至少 2 板", stocks: review.consecutive_limit_up.map((item) => reviewStock(item, `${item.board_count ?? "--"} 板 · 连续收盘涨停`)) },
    { label: "高度层级", value: new Set(review.consecutive_limit_up.map((item) => item.board_count)).size, source: "真实日线分组", unavailableReason: "该数值统计连板高度层级，不对应单一股票筛选；请点击“连板股票”查看逐股明细。" },
    { label: "历史覆盖", value: coverageLabel, source: `${review.history_ready_count}/${review.universe_count}`, unavailableReason: "当前接口仅返回历史覆盖聚合值，暂无缺失股票成员级明细。" },
  ] : variant === "first-board" ? [
    { label: "首板数量", value: review.first_limit_up.length, source: "上一日未涨停", stocks: review.first_limit_up.map((item) => reviewStock(item, "最新交易日首次收盘封板，上一交易日未涨停")) },
    { label: "成交过亿", value: review.first_limit_up.filter((item) => { const value = numberValue(item.amount_yi); return value !== null && value >= 1; }).length, source: "日成交额", stocks: review.first_limit_up.filter((item) => (numberValue(item.amount_yi) ?? 0) >= 1).map((item) => reviewStock(item, `首板且成交额 ${optionalValue(item.amount_yi, "亿")}`)) },
    { label: "平均涨幅", value: optionalValue(average(review.first_limit_up.map((item) => numberValue(item.change_percent)).filter((value): value is number => value !== null)), "%"), source: "最新交易日", unavailableReason: "平均值用于描述首板样本整体表现；请点击“首板数量”查看构成股票。" },
    { label: "历史覆盖", value: coverageLabel, source: `${review.history_ready_count}/${review.universe_count}`, unavailableReason: "当前接口仅返回历史覆盖聚合值，暂无缺失股票成员级明细。" },
  ] : variant === "dragon-tiger" ? [
    { label: "上榜股票", value: review.dragon_tiger.length, source: "公开榜单", stocks: review.dragon_tiger.map((item) => ({ symbol: item.symbol, name: item.name || "名称待补齐", reason: item.reason, value: signedYi(item.net_amount_yi) })) },
    { label: "净买入", value: review.dragon_tiger.filter((item) => Number(item.net_amount_yi) > 0).length, source: "按公开净额", stocks: review.dragon_tiger.filter((item) => Number(item.net_amount_yi) > 0).map((item) => ({ symbol: item.symbol, name: item.name || "名称待补齐", reason: `龙虎榜净买入 · ${item.reason}`, value: signedYi(item.net_amount_yi) })) },
    { label: "席位明细", value: review.dragon_tiger.reduce((sum, item) => sum + item.seats.length, 0), source: "真实席位记录", stocks: review.dragon_tiger.filter((item) => item.seats.length > 0).map((item) => ({ symbol: item.symbol, name: item.name || "名称待补齐", reason: `${item.seats.length} 条真实席位记录`, value: signedYi(item.net_amount_yi) })) },
    { label: "榜单日期", value: review.dragon_tiger[0]?.trade_date ?? "--", source: "缓存可追溯", unavailableReason: "日期是榜单时间口径，不对应股票筛选；请点击“上榜股票”查看明细。" },
  ] : (() => {
    const target = variant === "volume-breakout" ? review.volume_breakouts
      : variant === "previous-high" ? review.previous_high_breakouts : review.low_position_volume;
    return [
      { label: "规则命中", value: target.length, source: "严格筛选", stocks: target.map((item) => reviewStock(item, variant === "volume-breakout" ? "60 日收盘新高且成交量放大" : variant === "previous-high" ? "突破前 20 日最高价且量能确认" : "120 日区间低位且成交量放大")) },
      { label: "最大量能", value: optionalValue(maxNullable(target.map((item) => numberValue(item.volume_multiple)).filter((value): value is number => value !== null)), "x"), source: "相对前 5 日均量", stocks: target.filter((item) => numberValue(item.volume_multiple) === maxNullable(target.map((row) => numberValue(row.volume_multiple)).filter((value): value is number => value !== null))).map((item) => reviewStock(item, `量能倍数 ${optionalValue(item.volume_multiple, "x")}`)) },
      { label: "成交过亿", value: target.filter((item) => { const value = numberValue(item.amount_yi); return value !== null && value >= 1; }).length, source: "日成交额", stocks: target.filter((item) => (numberValue(item.amount_yi) ?? 0) >= 1).map((item) => reviewStock(item, `规则命中且成交额 ${optionalValue(item.amount_yi, "亿")}`)) },
      { label: "历史覆盖", value: coverageLabel, source: `${review.history_ready_count}/${review.universe_count}`, unavailableReason: "当前接口仅返回历史覆盖聚合值，暂无缺失股票成员级明细。" },
    ];
  })();
  return <><div className="review-summary-grid">{rows.map((item, index) => { const parsed = numberValue(item.value); const meter = index === 3 ? coverage : parsed; return <article key={item.label} data-state={meter === null ? "unavailable" : "ready"} style={{ "--meter": `${meter === null ? 0 : Math.min(100, Math.max(6, meter))}%` } as CSSProperties}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><i /><span>{item.label}</span><b>{item.value}</b><small>{item.source}</small></DrilldownMetric></article>; })}</div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
}

function average(values: number[]): number | null {
  const valid = values.filter((value) => Number.isFinite(value));
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : null;
}

function maxNullable(values: number[]): number | null {
  const valid = values.filter((value) => Number.isFinite(value));
  return valid.length ? Math.max(...valid) : null;
}

function ReviewStockLink({ item, onOpenAShare }: { item: MarketReviewStock; onOpenAShare?: (symbol: string) => void }) {
  return onOpenAShare
    ? <button type="button" aria-label={`查看 ${item.symbol} ${item.name}`} onClick={(event) => { event.stopPropagation(); onOpenAShare(item.symbol); }}>{item.name}</button>
    : <b>{item.name}</b>;
}

function LimitLadder({ data, onOpenAShare }: { data: MarketOverviewResponse; onOpenAShare?: (symbol: string) => void }) {
  const rows = data.review?.consecutive_limit_up ?? [];
  if (!rows.length) return <Empty>{reviewDate(data)} 没有检测到至少 2 个交易日连续收盘涨停的股票。</Empty>;
  const validRows = rows.filter((item) => item.board_count !== null && Number.isFinite(item.board_count));
  const groups = [...new Map(validRows.map((item) => [item.board_count as number, validRows.filter((row) => row.board_count === item.board_count).length])).entries()].sort((a, b) => b[0] - a[0]);
  return <div className="review-ladder"><div className="review-height-badges">{groups.map(([height, count]) => <span key={height}><b>{height}板</b><strong>× {count}</strong></span>)}</div>{!groups.length && <Empty>连板记录存在，但连板高度字段不可用。</Empty>}<div className="distinct-table-scroll"><table className="distinct-table review-detail-table"><thead><tr><th>连板</th><th>代码 / 名称</th><th>涨停统计</th><th>收盘</th><th>涨跌幅</th><th>换手率</th><th>封板资金</th><th>炸板次数</th><th>首次封板</th></tr></thead><tbody>{rows.map((item) => <tr key={item.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(item.symbol) : undefined, `查看 ${item.symbol} ${item.name}`)}><td><em className="board-badge">{optionalValue(item.board_count, "板")}</em></td><td><span>{item.symbol}<ReviewStockLink item={item} onOpenAShare={onOpenAShare} /></span></td><td>{optionalValue(item.limit_statistics)}</td><td>{optionalValue(item.close)}</td><td className={tone(numberValue(item.change_percent))}>{signedPercent(numberValue(item.change_percent))}</td><td>{optionalValue(item.turnover_rate, "%")}</td><td>{optionalValue(item.seal_amount_yi, "亿")}</td><td>{optionalValue(item.failed_limit_count)}</td><td>{optionalValue(item.first_seal_time)}</td></tr>)}</tbody></table></div><footer>交易日 {reviewDate(data)} · 封板资金、炸板次数和首次封板时间仅在盘中源提供时展示</footer></div>;
}

function FirstBoardTable({ data, onOpenAShare }: { data: MarketOverviewResponse; onOpenAShare?: (symbol: string) => void }) {
  const rows = data.review?.first_limit_up ?? [];
  if (!rows.length) return <Empty>{reviewDate(data)} 没有检测到“当日收盘涨停且前一交易日未涨停”的股票。</Empty>;
  return <div className="review-first-board"><div className="distinct-table-scroll"><table className="distinct-table review-detail-table"><thead><tr><th>代码 / 名称</th><th>收盘</th><th>涨跌幅</th><th>成交额</th><th>换手率</th><th>封板资金</th><th>炸板次数</th><th>首次封板</th></tr></thead><tbody>{rows.slice(0, 60).map((item) => <tr key={item.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(item.symbol) : undefined, `查看 ${item.symbol} ${item.name}`)}><td><span>{item.symbol}<ReviewStockLink item={item} onOpenAShare={onOpenAShare} /></span></td><td>{optionalValue(item.close)}</td><td className={tone(numberValue(item.change_percent))}>{signedPercent(numberValue(item.change_percent))}</td><td>{optionalValue(item.amount_yi, "亿")}</td><td>{optionalValue(item.turnover_rate, "%")}</td><td>{optionalValue(item.seal_amount_yi, "亿")}</td><td>{optionalValue(item.failed_limit_count)}</td><td>{optionalValue(item.first_seal_time)}</td></tr>)}</tbody></table></div><footer>共 {rows.length} 只 · 当前显示前 {Math.min(60, rows.length)} 只 · 交易日 {reviewDate(data)}</footer></div>;
}

function SectorPerformance({ data, model }: { data: MarketOverviewResponse; model: WorkspaceMarketModel }) {
  const sectors = [...model.sectors].filter((sector) => known(sector.change)).sort((a, b) => compareDesc(a.change, b.change)).slice(0, 25);
  if (!sectors.length) return <Empty>本地板块快照当前没有可验证的涨跌数据。</Empty>;
  const max = Math.max(1, ...sectors.map((item) => Math.abs(item.change ?? 0)));
  return <div className="sector-performance"><div className="sector-diverging-chart">{sectors.map((sector) => <article key={sector.sector_id}><b>{sector.name}</b><div><i className={tone(sector.change)} style={{ width: `${Math.abs(sector.change ?? 0) / max * 50}%` }} /></div><strong className={tone(sector.change)}>{signedPercent(sector.change)}</strong></article>)}</div><div className="distinct-table-scroll"><table className="distinct-table"><thead><tr><th>板块</th><th>涨跌幅</th><th>公司家数</th><th>上涨 / 下跌</th><th>总成交额</th><th>涨停数</th><th>领涨股票</th></tr></thead><tbody>{sectors.slice(0, 15).map((sector) => { const leader = (data.sector_stocks[sector.sector_id] ?? []).map((item) => ({ item, change: numberValue(item.change_percent) })).filter((entry) => known(entry.change)).sort((a, b) => compareDesc(a.change, b.change))[0]?.item; return <tr key={sector.sector_id}><td>{sector.name}</td><td className={tone(sector.change)}>{signedPercent(sector.change)}</td><td>{sector.stock_count}</td><td>{sector.rising_count} / {sector.falling_count}</td><td>{optionalValue(sector.amount, "亿")}</td><td>{sector.limit_up_count}</td><td>{leader ? `${leader.name} ${signedPercent(numberValue(leader.change_percent))}` : "--"}</td></tr>; })}</tbody></table></div></div>;
}

function BreakoutTable({ data, variant, onOpenAShare }: { data: MarketOverviewResponse; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const review = data.review;
  const rows = variant === "volume-breakout" ? review?.volume_breakouts ?? []
    : variant === "previous-high" ? review?.previous_high_breakouts ?? [] : review?.low_position_volume ?? [];
  const emptyText = variant === "volume-breakout" ? "没有股票同时满足 60 日收盘新高和量能 >= 1.8 倍。"
    : variant === "previous-high" ? "没有股票同时突破前 20 日最高价并得到量能确认。" : "没有股票同时位于 120 日区间下部 30% 且量能 >= 1.5 倍。";
  if (!rows.length) return <Empty>{reviewDate(data)} {emptyText}</Empty>;
  const volumes = rows.map((item) => numberValue(item.volume_multiple)).filter((value): value is number => value !== null);
  const maxVolume = volumes.length ? Math.max(...volumes) : null;
  const averageVolume = volumes.length ? volumes.reduce((sum, value) => sum + value, 0) / volumes.length : null;
  const title = variant === "volume-breakout" ? "放量突破强度" : variant === "previous-high" ? "突破前高强度" : "低位放量强度";
  const rule = variant === "volume-breakout" ? "收盘达到此前 60 日最高收盘 · 成交量 / 前 5 日均量 >= 1.8" : variant === "previous-high" ? "收盘突破此前 20 日最高价 · 成交量 / 前 5 日均量 >= 1.2" : "120 日区间位置 <= 30% · 成交量 / 前 5 日均量 >= 1.5";
  return <div className="breakout-review"><header>{rule}</header><div className="breakout-strength" data-testid="breakout-strength-meter" aria-label={title}><div><b>{title}</b><span>量能倍数越高，突破证据越强</span></div><strong>{averageVolume === null ? "--" : `${averageVolume.toFixed(2)}x`}</strong><i><em style={{ width: `${maxVolume === null ? 0 : Math.min(100, maxVolume / 3 * 100)}%` }} /></i><small>样本 {rows.length} 只 · 最大量能 {maxVolume === null ? "--" : `${maxVolume.toFixed(2)}x`}</small></div><div className="distinct-table-scroll"><table className="distinct-table review-detail-table"><thead><tr><th>代码 / 名称</th><th>收盘</th><th>涨跌幅</th><th>量能倍数</th><th>成交额</th>{variant !== "low-position" && <th>参考前高</th>}{variant === "low-position" && <th>区间位置</th>}<th>窗口</th></tr></thead><tbody>{rows.map((item) => { const volume = numberValue(item.volume_multiple); return <tr key={item.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(item.symbol) : undefined, `查看 ${item.symbol} ${item.name}`)}><td><span>{item.symbol}<ReviewStockLink item={item} onOpenAShare={onOpenAShare} /></span></td><td>{optionalValue(item.close)}</td><td className={tone(numberValue(item.change_percent))}>{signedPercent(numberValue(item.change_percent))}</td><td><em className="volume-multiple">{volume === null ? "--" : `${volume.toFixed(2)}x`}</em></td><td>{optionalValue(item.amount_yi, "亿")}</td>{variant !== "low-position" && <td>{optionalValue(item.reference_high)}</td>}{variant === "low-position" && <td>{optionalValue(item.range_position_percent, "%")}</td>}<td>{optionalValue(item.window_days, "日")}</td></tr>; })}</tbody></table></div></div>;
}

function DragonTigerBoard({ data, onOpenAShare }: { data: MarketOverviewResponse; onOpenAShare?: (symbol: string) => void }) {
  const rows = data.review?.dragon_tiger ?? [];
  const [selectedSymbol, setSelectedSymbol] = useState(rows[0]?.symbol ?? "");
  if (!hasDragonTigerEvidence(data.review)) return <Empty>龙虎榜公开接口当前不可用，且本地没有可用的真实缓存。</Empty>;
  if (!rows.length) return <Empty>{reviewDate(data)} 公开龙虎榜没有上榜股票。</Empty>;
  const selected = rows.find((item) => item.symbol === selectedSymbol) ?? rows[0];
  const money = (value: string | null | undefined) => { const parsed = numberValue(value); return parsed === null ? "--" : `${parsed >= 0 ? "+" : ""}${parsed}亿`; };
  const buyAmount = numberValue(selected.buy_amount_yi);
  const sellAmount = numberValue(selected.sell_amount_yi);
  const maxFlow = Math.max(1, buyAmount ?? 0, sellAmount ?? 0);
  return <div className="dragon-tiger-workbench"><aside>{rows.map((item) => <button type="button" className={item.symbol === selected.symbol ? "active" : ""} key={`${item.trade_date}-${item.symbol}`} onClick={() => setSelectedSymbol(item.symbol)}><span><b>{item.name}</b><small>{item.symbol} · {item.trade_date}</small></span><strong className={tone(numberValue(item.net_amount_yi))}>{money(item.net_amount_yi)}</strong></button>)}</aside><section><header><div>{onOpenAShare ? <button type="button" onClick={() => onOpenAShare(selected.symbol)}>{selected.name} <small>{selected.symbol}</small></button> : <h4>{selected.name} <small>{selected.symbol}</small></h4>}<p>{selected.reason}</p></div><span><small>榜单净额</small><b className={tone(numberValue(selected.net_amount_yi))}>{money(selected.net_amount_yi)}</b></span></header><div className="dragon-tiger-totals"><article><small>买入额</small><b>{optionalValue(selected.buy_amount_yi, "亿")}</b></article><article><small>卖出额</small><b>{optionalValue(selected.sell_amount_yi, "亿")}</b></article><article><small>净额</small><b className={tone(numberValue(selected.net_amount_yi))}>{money(selected.net_amount_yi)}</b></article><article><small>涨跌幅</small><b className={tone(numberValue(selected.change_percent))}>{signedPercent(numberValue(selected.change_percent))}</b></article></div><div className="dragon-tiger-flow" data-testid="dragon-tiger-flow-meter" aria-label="龙虎榜买入卖出对照"><header><b>买入 / 卖出对照</b><span>只使用公开席位买卖金额</span></header><div className="flow-bars"><span>买入</span><i className="up"><em style={{ width: `${buyAmount === null ? 0 : buyAmount / maxFlow * 100}%` }} /></i><strong>{optionalValue(selected.buy_amount_yi, "亿")}</strong><span>卖出</span><i className="down"><em style={{ width: `${sellAmount === null ? 0 : sellAmount / maxFlow * 100}%` }} /></i><strong>{optionalValue(selected.sell_amount_yi, "亿")}</strong></div></div>{selected.seats.length ? <div className="distinct-table-scroll"><table className="distinct-table"><thead><tr><th>方向</th><th>席位</th><th>买入额</th><th>卖出额</th><th>净额</th></tr></thead><tbody>{selected.seats.map((seat, index) => <tr key={`${seat.seat_name}-${index}`}><td>{seat.direction === "buy" ? "买入" : seat.direction === "sell" ? "卖出" : "双向"}</td><td>{seat.seat_name}</td><td>{optionalValue(seat.buy_amount_yi, "亿")}</td><td>{optionalValue(seat.sell_amount_yi, "亿")}</td><td className={tone(numberValue(seat.net_amount_yi))}>{money(seat.net_amount_yi)}</td></tr>)}</tbody></table></div> : <Empty>榜单股票真实可用，但席位明细接口未返回记录。</Empty>}</section></div>;
}

function SeatTracker({ data, actions }: { data: MarketOverviewResponse; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  const seats = data.review?.dragon_tiger.flatMap((stock) => stock.seats.map((seat) => ({ ...seat, stockName: stock.name, stockReason: stock.reason }))) ?? [];
  if (!hasDragonTigerEvidence(data.review)) return <Empty>龙虎榜公开接口当前不可用，且本地没有可追溯缓存。</Empty>;
  if (!seats.length) return <Empty>{reviewDate(data)} 龙虎榜没有返回带名称和买卖金额的席位明细。</Empty>;
  const grouped = new Map<string, { buy: number; sell: number; net: number; stocks: Map<string, DrilldownStock> }>();
  seats.forEach((seat) => {
    const current = grouped.get(seat.seat_name) ?? { buy: 0, sell: 0, net: 0, stocks: new Map<string, DrilldownStock>() };
    const buy = numberValue(seat.buy_amount_yi);
    const sell = numberValue(seat.sell_amount_yi);
    const net = numberValue(seat.net_amount_yi);
    if (buy !== null) current.buy += buy;
    if (sell !== null) current.sell += sell;
    if (net !== null) current.net += net;
    current.stocks.set(seat.symbol, { symbol: seat.symbol, name: seat.stockName?.trim() || "名称待补齐", reason: `席位：${seat.seat_name} · ${seat.stockReason}`, value: optionalValue(seat.net_amount_yi, "亿") });
    grouped.set(seat.seat_name, current);
  });
  const rows = [...grouped.entries()].sort((a, b) => Math.abs(b[1].net) - Math.abs(a[1].net));
  return <><div className="distinct-table-scroll"><table className="distinct-table seat-tracker-table"><thead><tr><th>席位名称</th><th>涉及股票</th><th>买入额</th><th>卖出额</th><th>净额</th><th>方向</th></tr></thead><tbody>{rows.map(([name, row]) => {
    const item: MetricDrilldownSelection = { label: `${name}涉及股票`, value: row.stocks.size, source: "公开龙虎榜席位明细", stocks: [...row.stocks.values()] };
    return <tr key={name}><td><b>{name}</b></td><td><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><strong>{row.stocks.size}</strong></DrilldownMetric></td><td>{row.buy.toFixed(2)}亿</td><td>{row.sell.toFixed(2)}亿</td><td className={tone(row.net)}>{row.net >= 0 ? "+" : ""}{row.net.toFixed(2)}亿</td><td><span className={`seat-direction-tag ${tone(row.net)}`}>{row.net > 0 ? "净买入" : row.net < 0 ? "净卖出" : "买卖平衡"}</span></td></tr>;
  })}</tbody></table></div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
}

function SeatDirection({ data, actions }: { data: MarketOverviewResponse; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  const stocks = data.review?.dragon_tiger ?? [];
  if (!hasDragonTigerEvidence(data.review)) return <Empty>龙虎榜公开接口当前不可用，且本地没有可追溯缓存。</Empty>;
  if (!stocks.length) return <Empty>{reviewDate(data)} 龙虎榜没有上榜股票，不能生成席位方向。</Empty>;
  const validStocks = stocks.filter((item) => numberValue(item.net_amount_yi) !== null);
  if (!validStocks.length) return <Empty>{reviewDate(data)} 龙虎榜净额字段不可用，不能生成方向分组。</Empty>;
  const groups = [
    ["净买入", validStocks.filter((item) => Number(item.net_amount_yi) > 0), "up"],
    ["净卖出", validStocks.filter((item) => Number(item.net_amount_yi) < 0), "down"],
    ["买卖平衡", validStocks.filter((item) => Number(item.net_amount_yi) === 0), "flat"],
  ] as const;
  return <><div className="seat-direction-dashboard">{groups.map(([label, rows, itemTone]) => {
    const net = rows.reduce((sum, item) => sum + Number(item.net_amount_yi), 0);
    const leader = [...rows].sort((a, b) => Math.abs(Number(b.net_amount_yi)) - Math.abs(Number(a.net_amount_yi)))[0];
    const item: MetricDrilldownSelection = { label, value: rows.length, source: "公开龙虎榜单股净额方向", stocks: rows.map((stock) => ({ symbol: stock.symbol, name: stock.name?.trim() || "名称待补齐", reason: `${label} · ${stock.reason}`, value: signedYi(stock.net_amount_yi) })) };
    return <section key={label} className={itemTone}><header><DrilldownMetric item={item} selected={selection?.label === label} onSelect={setSelection}><span>{label}</span><b>{rows.length} 只</b></DrilldownMetric></header><strong>{net >= 0 ? "+" : ""}{net.toFixed(2)}亿</strong><p>{leader ? `${leader.name} ${leader.symbol}` : "当前无记录"}</p><small>{leader ? `最大单股净额 ${Number(leader.net_amount_yi) >= 0 ? "+" : ""}${leader.net_amount_yi}亿` : "不生成替代数据"}</small></section>;
  })}</div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
}

function HistoryAudit({ data, variant }: { data: MarketOverviewResponse; variant: string }) {
  const review = data.review;
  const historicalRows = variant === "new-high" ? (review?.new_high_100 ?? [])
    : variant === "previous-limit" ? (review?.previous_limit_up ?? []) : [];
  const coverage = review && review.universe_count > 0 && review.history_ready_count > 0
    ? `${review.history_ready_count}/${review.universe_count} (${(review.history_ready_count / review.universe_count * 100).toFixed(1)}%)`
    : "未接入";
  const labels = variant === "new-high" ? ["所需窗口", "100 个交易日", "日线覆盖", coverage]
    : variant === "previous-limit" ? ["所需日期", "上一交易日", "复盘日期", review?.latest_trade_date ?? "未接入"]
    : variant === "consecutive-days" ? ["所需连续窗口", "至少 2 个交易日", "连板记录", review ? `${review.consecutive_limit_up.length} 只` : "未接入"]
    : variant === "trend-stage" ? ["趋势前提", "先确认百日新高", "当前状态", "逐股趋势字段未接入"]
    : ["统计区间", "需明确起止日", "有效样本", "未选择区间"];
  const note = variant === "new-high"
    ? historicalRows.length ? `已返回 ${historicalRows.length} 只百日新高股票，趋势分布将基于逐股收盘与参考高点计算。` : "当前复盘接口尚未返回百日新高逐股结果，不能用今日涨幅替代。"
    : variant === "previous-limit"
      ? historicalRows.length ? `已返回 ${historicalRows.length} 只昨涨停次日反馈股票，分组将基于当前收盘相对前一日收盘计算。` : "当前复盘接口尚未返回上一交易日涨停反馈逐股结果，不能用当前涨停状态替代。"
      : variant === "consecutive-days"
        ? "连板结果只在本地日线窗口完整时统计。"
        : "页面保留证据边界，不用代表股票快照伪造历史结论。";
  return <div className="history-audit"><AlertTriangle size={28} /><div><small>{labels[0]}</small><b>{labels[1]}</b></div><div><small>{labels[2]}</small><b>{labels[3]}</b></div><p>{note}</p></div>;
}

function HistoricalRankingTable({ data, variant, onOpenAShare }: { data: MarketOverviewResponse; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const rows = variant === "verified-only" ? (data.review?.new_high_100 ?? []) : (data.review?.previous_limit_up ?? []);
  if (!rows.length) return <HistoricalRankingNotice variant={variant} />;
  const isPrevious = variant === "previous-only";
  const title = isPrevious ? "上一交易日涨停 · 次日反馈" : "收盘创 100 日新高";
  return <div className="historical-ranking-table">
    <div className="historical-ranking-heading"><b>{title}</b><span>{rows.length} 只 · 交易日 {data.review?.latest_trade_date ?? "未接入"}</span></div>
    <div className="distinct-table-scroll"><table className="distinct-table review-detail-table"><thead><tr><th>代码 / 名称</th><th>当前收盘</th><th>当前涨跌</th>{isPrevious && <><th>前一日收盘</th><th>前一日涨跌</th></>}{!isPrevious && <><th>100 日参考高点</th><th>突破幅度</th></>}<th>成交额</th><th>窗口</th></tr></thead><tbody>{rows.slice(0, 60).map((item) => {
      const close = numberValue(item.close);
      const referenceHigh = numberValue(item.reference_high);
      const breakout = close !== null && referenceHigh !== null && referenceHigh > 0 ? (close / referenceHigh - 1) * 100 : null;
      return <tr key={`${item.trade_date}-${item.symbol}`} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(item.symbol) : undefined, `查看 ${item.symbol} ${item.name}`)}><td><span>{item.symbol}<ReviewStockLink item={item} onOpenAShare={onOpenAShare} /></span></td><td>{optionalValue(item.close)}</td><td className={tone(numberValue(item.change_percent))}>{signedPercent(numberValue(item.change_percent))}</td>{isPrevious && <><td>{optionalValue(item.prior_close)}</td><td className={tone(numberValue(item.prior_change_percent))}>{signedPercent(numberValue(item.prior_change_percent))}</td></>}{!isPrevious && <><td>{optionalValue(item.reference_high)}</td><td className={tone(breakout)}>{signedPercent(breakout)}</td></>}<td>{optionalValue(item.amount_yi, "亿")}</td><td>{optionalValue(item.window_days, "日")}</td></tr>;
    })}</tbody></table></div>
    <footer>来源 {data.review?.source ?? "未接入"} · 只展示复盘接口返回的逐股结果，不用代表快照代替历史样本</footer>
  </div>;
}

function HeightPyramid({ data, actions }: { data: MarketOverviewResponse; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  if (!data.review) return <Empty>本地日线复盘尚未完成，不能用当前涨幅推断连板高度。</Empty>;
  const rows = data.review.consecutive_limit_up;
  if (!rows.length) return <Empty>{reviewDate(data)} 没有检测到连续 2 个交易日收盘涨停的股票。</Empty>;
  const heights = rows.map((item) => item.board_count).filter((value): value is number => value !== null && Number.isFinite(value));
  if (!heights.length) return <Empty>{reviewDate(data)} 连板记录存在，但连板高度字段不可用。</Empty>;
  const max = Math.max(...heights);
  return <><div className="height-pyramid" data-layout="compact-grid">{Array.from({ length: Math.max(1, max - 1) }, (_, index) => max - index).map((level) => {
    const members = rows.filter((item) => item.board_count === level);
    const item: MetricDrilldownSelection = { label: `${level} 板`, value: members.length, source: "本地连续涨停日线", stocks: members.map((member) => reviewStock(member, `连续 ${level} 个交易日收盘涨停`)) };
    return <div key={level}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><b>{level} 板</b><span>{members.length}</span><small>{members.length ? "真实日线验证" : "该高度为空"}</small></DrilldownMetric></div>;
  })}</div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
}

function PromotionFunnel({ model, actions }: { model: WorkspaceMarketModel; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  const stages: MetricDrilldownSelection[] = [
    { label: "代表样本", value: model.stocks.length, source: "当前接口代表股票", stocks: model.stocks.map((stock) => derivedStock(stock, "进入当前代表股票样本")) },
    { label: "涨幅 > 5%", value: model.stocks.filter((stock) => known(stock.change) && stock.change > 5).length, source: "当前涨跌幅", stocks: model.stocks.filter((stock) => known(stock.change) && stock.change > 5).map((stock) => derivedStock(stock, `当前涨幅 ${signedPercent(stock.change)}`)) },
    { label: "当前封板", value: model.stocks.filter((stock) => stock.state === "limit_up").length, source: "严格现价状态", stocks: model.stocks.filter((stock) => stock.state === "limit_up").map((stock) => derivedStock(stock, "当前价格达到严格涨停状态")) },
    { label: "具备题材证据", value: model.stocks.filter((stock) => stock.themes.length > 0).length, source: "本地资讯关联", stocks: model.stocks.filter((stock) => stock.themes.length > 0).map((stock) => derivedStock(stock, `已关联题材：${stock.themes.join(" / ")}`)) },
  ];
  return <><div className="promotion-funnel" data-layout="compact-grid">{stages.map((item, index) => <article key={item.label}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><span>{index + 1}</span><b>{item.label}</b><strong>{item.value}</strong></DrilldownMetric></article>)}</div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
}

function LeaderLanes({ model, onOpenAShare }: { model: WorkspaceMarketModel; onOpenAShare?: (symbol: string) => void }) {
  const lanes = [
    ["前排封板", model.stocks.filter((stock) => stock.state === "limit_up")],
    ["容量强势", [...model.stocks].filter((stock) => known(stock.amount) && known(stock.change) && stock.amount > 0 && stock.change > 2).sort((a, b) => compareDesc(a.amount, b.amount))],
    ["跟随观察", model.stocks.filter((stock) => known(stock.change) && stock.change > 0 && stock.state === "active")],
    ["风险降级", model.stocks.filter((stock) => stock.state === "broken_limit_up" || stock.state === "limit_down")],
  ] as const;
  return <div className="leader-lanes">{lanes.map(([label, stocks]) => <section key={label}><header><b>{label}</b><span>{stocks.length}</span></header>{stocks.slice(0, 8).map((stock) => <article key={stock.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(stock.symbol) : undefined, `查看 ${stock.symbol} ${stock.name}`)}><StockName stock={stock} onOpenAShare={onOpenAShare} /><small>{stock.symbol}</small><strong className={tone(stock.change)}>{signedPercent(stock.change)}</strong></article>)}</section>)}</div>;
}

function Distribution({ data, model, variant, actions }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  if (variant === "selected-window") return <HistoryAudit data={data} variant={variant} />;
  if (variant === "feedback" || variant === "distance-high") {
    const rows = variant === "feedback" ? (data.review?.previous_limit_up ?? []) : (data.review?.new_high_100 ?? []);
    if (!rows.length) return <HistoryAudit data={data} variant={variant === "feedback" ? "previous-limit" : "new-high"} />;
    const valuedRows = rows.map((item) => {
      const close = numberValue(item.close);
      if (variant === "feedback") {
        const prior = numberValue(item.prior_close);
        return { item, value: close !== null && prior !== null && prior > 0 ? (close / prior - 1) * 100 : null };
      }
      const high = numberValue(item.reference_high);
      return { item, value: close !== null && high !== null && high > 0 ? (close / high - 1) * 100 : null };
    }).filter((row): row is { item: MarketReviewStock; value: number } => row.value !== null);
    if (!valuedRows.length) return <HistoryAudit data={data} variant={variant === "feedback" ? "previous-limit" : "new-high"} />;
    const bins: Array<readonly [string, (value: number) => boolean, string]> = variant === "feedback" ? [
      ["回撤 <= -3%", (value: number) => value <= -3, "down"],
      ["回撤 -3% ~ 0", (value: number) => value > -3 && value < 0, "down"],
      ["横盘 0% ~ 3%", (value: number) => value >= 0 && value < 3, "flat"],
      ["反弹 >= 3%", (value: number) => value >= 3, "up"],
    ] : [
      ["突破 0% ~ 3%", (value: number) => value >= 0 && value < 3, "up"],
      ["突破 3% ~ 8%", (value: number) => value >= 3 && value < 8, "up"],
      ["突破 >= 8%", (value: number) => value >= 8, "up"],
    ];
    const items: Array<MetricDrilldownSelection & { itemTone: string }> = bins.map(([label, predicate, itemTone]) => {
      const matched = valuedRows.filter((row) => predicate(row.value));
      return { label, value: matched.length, source: variant === "feedback" ? "昨涨停次日反馈" : "百日新高突破幅度", itemTone, stocks: matched.map(({ item, value }) => reviewStock(item, `${label} · ${signedPercent(value)}`)) };
    });
    const max = Math.max(1, ...items.map((item) => Number(item.value)));
    return <><div className="distribution-bars"><header className="distribution-heading"><b>{variant === "feedback" ? "昨涨停次日回撤/反弹" : "百日新高突破幅度"}</b><span>{valuedRows.length} 只有效样本</span></header>{items.map((item) => <article key={item.label}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><span>{item.label}</span><div className={item.itemTone}><i style={{ width: `${Number(item.value) / max * 100}%` }} /></div><b>{item.value}</b></DrilldownMetric></article>)}<footer>{variant === "feedback" ? "回撤/反弹按当前收盘相对前一交易日收盘计算。" : "突破幅度按当前收盘相对前 100 个交易日最高收盘计算。"}</footer></div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
  }
  const stockBins = variant === "score-parts" ? [
    ["人气分 0-20", (stock: DerivedStock) => known(stock.attentionScore) && stock.attentionScore < 20, "flat"],
    ["人气分 20-40", (stock: DerivedStock) => known(stock.attentionScore) && stock.attentionScore >= 20 && stock.attentionScore < 40, "flat"],
    ["人气分 40-60", (stock: DerivedStock) => known(stock.attentionScore) && stock.attentionScore >= 40 && stock.attentionScore < 60, "up"],
    ["人气分 60-80", (stock: DerivedStock) => known(stock.attentionScore) && stock.attentionScore >= 60 && stock.attentionScore < 80, "up"],
    ["人气分 80-100", (stock: DerivedStock) => known(stock.attentionScore) && stock.attentionScore >= 80, "up"],
  ] as const : [
    ["跌幅 > 7%", (stock: DerivedStock) => known(stock.change) && stock.change <= -7, "down"],
    ["-7% ~ 0", (stock: DerivedStock) => known(stock.change) && stock.change > -7 && stock.change < 0, "down"],
    ["平盘", (stock: DerivedStock) => known(stock.change) && stock.change === 0, "flat"],
    ["0 ~ 7%", (stock: DerivedStock) => known(stock.change) && stock.change > 0 && stock.change < 7, "up"],
    ["涨幅 >= 7%", (stock: DerivedStock) => known(stock.change) && stock.change >= 7, "up"],
  ] as const;
  const sectorBins = [
    ["板块强度 0-20", model.sectors.filter((sector) => known(sector.strengthScore) && sector.strengthScore < 20).length, "down"],
    ["板块强度 20-40", model.sectors.filter((sector) => known(sector.strengthScore) && sector.strengthScore >= 20 && sector.strengthScore < 40).length, "flat"],
    ["板块强度 40-60", model.sectors.filter((sector) => known(sector.strengthScore) && sector.strengthScore >= 40 && sector.strengthScore < 60).length, "flat"],
    ["板块强度 60-80", model.sectors.filter((sector) => known(sector.strengthScore) && sector.strengthScore >= 60 && sector.strengthScore < 80).length, "up"],
    ["板块强度 80-100", model.sectors.filter((sector) => known(sector.strengthScore) && sector.strengthScore >= 80).length, "up"],
  ] as const;
  const items: Array<MetricDrilldownSelection & { itemTone: string }> = variant === "sector-bands"
    ? sectorBins.map(([label, value, itemTone]) => ({ label, value, source: "本地板块强度", itemTone, unavailableReason: "该柱统计板块数量，不是股票数量；请在板块赛道的热力图和矩阵中查看对应板块。" }))
    : stockBins.map(([label, predicate, itemTone]) => {
      const matched = model.stocks.filter(predicate);
      return { label, value: matched.length, source: variant === "score-parts" ? "代表股票人气分" : "代表股票涨跌幅", itemTone, stocks: matched.map((stock) => derivedStock(stock, variant === "score-parts" ? `人气分 ${optionalValue(stock.attentionScore)}` : `当前涨跌 ${signedPercent(stock.change)}`)) };
    });
  const max = Math.max(1, ...items.map((item) => Number(item.value)));
  const footer = variant === "score-parts"
    ? "人气分为量价与题材关联的观察性合成分，只覆盖接口代表股票。"
    : variant === "sector-bands"
      ? "板块强度由涨跌幅、上涨广度和涨停密度确定性派生，只覆盖本地板块快照。"
      : `全市场广度：上涨 ${data.breadth.rising_count} / 下跌 ${data.breadth.falling_count}；柱状分布仅覆盖接口代表股票。`;
  return <><div className="distribution-bars">{items.map((item) => <article key={item.label}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><span>{item.label}</span><div className={item.itemTone}><i style={{ width: `${Number(item.value) / max * 100}%` }} /></div><b>{item.value}</b></DrilldownMetric></article>)}<footer>{footer}</footer></div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
}

function SevenRankings({ model, onOpenAShare }: { model: WorkspaceMarketModel; onOpenAShare?: (symbol: string) => void }) {
  const top = (sort: (a: DerivedStock, b: DerivedStock) => number) => [...model.stocks].sort(sort)[0];
  const anomalyCountBySymbol = new Map<string, number>();
  model.anomalies.forEach((event) => event.symbols.forEach((symbol) => anomalyCountBySymbol.set(symbol, (anomalyCountBySymbol.get(symbol) ?? 0) + 1)));
  const topAnomalyStock = [...model.stocks]
    .filter((stock) => anomalyCountBySymbol.has(stock.symbol))
    .filter((stock) => known(stock.attentionScore))
    .sort((a, b) => (anomalyCountBySymbol.get(b.symbol) ?? 0) - (anomalyCountBySymbol.get(a.symbol) ?? 0) || compareDesc(a.attentionScore, b.attentionScore))[0];
  const ranks = [
    ["涨幅", top((a, b) => compareDesc(a.change, b.change))], ["成交", top((a, b) => compareDesc(a.amount, b.amount))],
    ["振幅", top((a, b) => compareDesc(a.amplitude, b.amplitude))], ["高开", top((a, b) => compareDesc(a.gap, b.gap))],
    ["封板", model.stocks.find((stock) => stock.state === "limit_up")], ["题材", top((a, b) => b.themes.length - a.themes.length)],
    ["异动", topAnomalyStock],
  ] as const;
  return <div className="seven-rankings">{ranks.map(([label, stock], index) => <article key={label} {...interactiveTargetProps(stock && onOpenAShare ? () => onOpenAShare(stock.symbol) : undefined, stock ? `查看 ${stock.symbol} ${stock.name}` : "")}><span>0{index + 1}</span><small>{label}榜首</small><b>{stock?.name ?? "暂无样本"}</b><em>{stock ? stock.symbol : "--"}</em><strong>{stock ? signedPercent(stock.change) : "--"}</strong></article>)}</div>;
}

function StatisticsPivot({ data, model, variant, actions }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  const isAnomalyPivot = variant === "direction-theme-time";
  const anomalyStocks = (direction: "positive" | "negative" | "uncertain") => model.anomalies
    .filter((item) => item.direction === direction)
    .flatMap((item) => item.symbols.map((symbol) => ({
      symbol,
      name: stockNameForSymbol(model, symbol),
      reason: `${item.label} · ${item.headline}`,
    })));
  const rows: MetricDrilldownSelection[] = isAnomalyPivot ? [
    { label: "正向异动", value: model.anomalies.filter((item) => item.direction === "positive").length, source: "本地异动库", stocks: anomalyStocks("positive") },
    { label: "风险异动", value: model.anomalies.filter((item) => item.direction === "negative").length, source: "本地异动库", stocks: anomalyStocks("negative") },
    { label: "待确认", value: model.anomalies.filter((item) => item.direction === "uncertain").length, source: "本地异动库", stocks: anomalyStocks("uncertain") },
    { label: "关联题材", value: model.themes.length, source: "资讯与异动去重", unavailableReason: "该数值统计去重题材数量，不对应单一股票集合；请进入异动题材排行查看题材及其关联股票。" },
  ] : [
    { label: "上涨家数", value: data.breadth.rising_count, source: "全市场快照", unavailableReason: "当前接口仅返回全市场聚合值，暂无成员级明细；代表股票样本不能冒充全市场上涨名单。" },
    { label: "下跌家数", value: data.breadth.falling_count, source: "全市场快照", unavailableReason: "当前接口仅返回全市场聚合值，暂无成员级明细；代表股票样本不能冒充全市场下跌名单。" },
    { label: "涨停家数", value: data.limit_ecology.limit_up_count, source: "严格现价", stocks: stocksForVariant(model, "strict-limit").map((item) => derivedStock(item, "当前价格达到严格涨停状态")) },
    { label: "炸板家数", value: data.limit_ecology.broken_limit_up_count, source: "触板未封", stocks: stocksForVariant(model, "strict-broken").map((item) => derivedStock(item, "最高价触及涨停但当前未封住")) },
    { label: "板块样本", value: model.sectors.length, source: "本地板块", unavailableReason: "该数值对应板块样本，不是股票数量；请进入板块相关菜单查看板块及已加载成分股。" },
    { label: "A 股资讯", value: model.news.length, source: "已关联代码", stocks: [...new Set(model.news.flatMap((item) => item.symbols))].map((symbol) => ({ symbol, name: stockNameForSymbol(model, symbol), reason: "本地资讯已关联该 A 股代码" })) },
  ];
  return <><div className={`statistics-pivot${isAnomalyPivot ? " statistics-pivot-four" : ""}`}>{rows.map((item) => <article key={item.label}><DrilldownMetric item={item} selected={selection?.label === item.label} onSelect={setSelection}><span>{item.label}</span><b>{item.value}</b><small>{item.source}</small></DrilldownMetric></article>)}</div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
}

function EventCalendar({ data, model, onOpenAShare }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; onOpenAShare?: (symbol: string) => void }) {
  const linkedNews = model.news.filter((item) => item.symbols.length > 0);
  const officialLabels = { subscription: "申购日", allotment: "中签日", listing: "上市日" } as const;
  const calendarItems = [
    ...(data.official_events ?? []).map((item) => ({
      id: item.event_id, day: item.event_date, time: officialLabels[item.event_type], symbols: [item.code],
      title: `${item.name} ${officialLabels[item.event_type]}`, source: item.source,
      code: item.code, themes: [item.kind], summary: `${item.kind} · ${item.code}`,
      official: true, verified: item.quality === "ready", observedAt: item.observed_at,
    })),
    ...linkedNews.map((item) => ({
      id: item.event_id, day: item.occurred_at.slice(0, 10), time: timeLabel(item.occurred_at).slice(-5), symbols: item.symbols,
      title: item.headline, source: item.source, code: item.symbols.join("、"), themes: item.themes,
      summary: item.summary || "当前来源没有提供可验证摘要，请以原始标题和来源为准。",
      official: false, verified: item.review_state === "verified", observedAt: item.occurred_at,
    })),
  ].sort((left, right) => left.day.localeCompare(right.day) || Number(right.official) - Number(left.official));
  const [selectedEventId, setSelectedEventId] = useState(calendarItems[0]?.id ?? "");
  if (!calendarItems.length) return <Empty>没有官方事项日期或带时间戳且已关联 A 股的本地资讯。</Empty>;
  const selected = calendarItems.find((item) => item.id === selectedEventId) ?? calendarItems[0];
  const groups = new Map<string, typeof calendarItems>();
  calendarItems.forEach((item) => {
    groups.set(item.day, [...(groups.get(item.day) ?? []), item]);
  });
  return <div className="event-calendar">
    <div className="event-calendar-index" aria-label="事件索引">{[...groups.entries()].map(([day, items]) => <section key={day}><header><CalendarDays size={18} /><div><b>{day}</b><small>{items.length} 项可核验事件</small></div></header>{items.slice(0, 12).map((item) => <button key={item.id} type="button" aria-label={`查看事件：${item.title}`} aria-pressed={selected.id === item.id} onClick={() => setSelectedEventId(item.id)}><time>{item.time}</time><span><b>{item.title}</b><small>{item.official ? "官方事项日期" : "资讯时间"} · {item.source} · {item.code || "未关联代码"}</small></span></button>)}</section>)}</div>
    <article className="event-calendar-detail" role="region" aria-label="当前事件详情">
      <header><span>{selected.official ? selected.day : timeLabel(selected.observedAt)}</span><em>{selected.verified ? "已核验" : "待复核"}</em></header>
      <h4>{selected.title}</h4>
      <p>{selected.summary}</p>
      <dl><div><dt>来源</dt><dd>{selected.source}</dd></div><div><dt>关联股票</dt><dd className="event-calendar-stock-links">{selected.symbols.length ? selected.symbols.map((symbol) => { const name = stockNameForSymbol(model, symbol); return onOpenAShare ? <button type="button" key={symbol} aria-label={`查看 ${symbol} ${name}`} onClick={() => onOpenAShare(symbol)}>{name}<small>{symbol}</small></button> : <span key={symbol}>{name}<small>{symbol}</small></span>; }) : "未关联"}</dd></div><div><dt>关联分类</dt><dd>{selected.themes.join(" / ") || "未归类"}</dd></div><div><dt>时间口径</dt><dd>{selected.official ? "通达信官方事项日期" : "资讯发生/入库时间，不替代官方事项日期"}</dd></div></dl>
    </article>
  </div>;
}

function ReviewColumns({ model, actions }: { model: WorkspaceMarketModel; actions: StockResearchActions }) {
  const [selection, setSelection] = useMetricDrilldown();
  const columns = [
    ["封板", model.stocks.filter((stock) => stock.state === "limit_up"), "sealed"],
    ["炸板", model.stocks.filter((stock) => stock.state === "broken_limit_up"), "broken"],
    ["跌停", model.stocks.filter((stock) => stock.state === "limit_down"), "down"],
  ] as const;
  return <><div className="review-columns">{columns.map(([label, stocks, className]) => {
    const item: MetricDrilldownSelection = { label, value: stocks.length, source: "严格现价状态", stocks: stocks.map((stock) => derivedStock(stock, `${label}状态 · 当前涨跌 ${signedPercent(stock.change)}`)) };
    return <section key={label} className={className}><header><DrilldownMetric item={item} selected={selection?.label === label} onSelect={setSelection}><b>{label}</b><strong>{stocks.length}</strong></DrilldownMetric></header>{stocks.slice(0, 10).map((stock) => <article key={stock.symbol}><span>{stock.name}<small>{stock.symbol}</small></span><b>{signedPercent(stock.change)}</b></article>)}{!stocks.length && <p>无严格记录</p>}</section>;
  })}</div><DrilldownRegion selection={selection} setSelection={setSelection} actions={actions} /></>;
}

function RuleGates({ data, model, variant }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string }) {
  if (variant === "deterministic") return <AuctionGates model={model} />;
  const quoteCoverage = data.market_data.universe_count > 0
    ? data.market_data.quote_count / data.market_data.universe_count
    : 0;
  const gates = variant === "ai-rules" ? [
    ["行情字段完整", quoteCoverage >= 0.8],
    ["题材关联可追溯", model.themes.some((theme) => theme.symbols.length > 0)],
    ["风险状态已排除", !model.stocks.some((stock) => stock.state === "limit_down" || stock.state === "broken_limit_up")],
    ["AI 只解释证据", true],
  ] : variant === "iwencai-local" ? [
    ["本地规则执行", true],
    ["不调用问财官方接口", true],
    ["行情字段可复核", quoteCoverage > 0],
    ["候选结果可追溯", model.stocks.length > 0],
  ] : variant === "next-day" ? [
    ["涨停当日不追买", true], ["次日只在触发后观察", true], ["炸板与跌停先降级", data.limit_ecology.broken_limit_up_count + data.limit_ecology.limit_down_count === 0],
  ] : variant === "leader-rules" ? [
    ["当前严格封板", data.limit_ecology.limit_up_count > 0], ["板块存在扩散", model.sectors.some((sector) => sector.limit_up_count >= 2)], ["资讯题材可追溯", model.themes.length > 0], ["历史连板已验证", false],
  ] : [
    ["行情覆盖 >= 80%", data.market_data.universe_count > 0 && data.market_data.quote_count / data.market_data.universe_count >= 0.8],
    ["市场风格已识别", Boolean(data.regime?.regime)], ["候选含真实行情", model.stocks.length > 0], ["题材证据可追溯", model.themes.length > 0],
  ];
  return <div className="vertical-gates">{gates.map(([label, pass], index) => <article key={String(label)} className={pass ? "pass" : "blocked"}><span>{index + 1}</span>{pass ? <CheckCircle2 /> : <XCircle />}<b>{label}</b><small>{pass ? "通过" : "阻断 / 待补证据"}</small></article>)}</div>;
}

function EvidenceMap({ model, variant, onOpenAShare }: { model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const focusSymbols = variant === "alert-links" ? new Set(model.anomalies.filter((item) => item.direction === "negative").flatMap((item) => item.symbols))
    : variant === "stock-news" && model.stocks[0] ? new Set([model.stocks[0].symbol]) : null;
  const discoveryThemes = variant === "discovery"
    ? new Set(model.themes.filter((item) => item.evidenceCount >= 2).map((item) => item.name))
    : null;
  const sourceNews = variant === "full-chain"
    ? model.news.filter((item) => item.review_state === "verified" && item.symbols.length > 0 && item.themes.length > 0)
    : ["theme-link", "source-count"].includes(variant)
      ? model.news.filter((item) => item.symbols.length > 0 && item.themes.length > 0)
      : discoveryThemes
        ? model.news.filter((item) => item.themes.some((theme) => discoveryThemes.has(theme)))
        : model.news;
  const news = focusSymbols ? sourceNews.filter((item) => item.symbols.some((symbol) => focusSymbols.has(symbol))) : sourceNews;
  const themes = focusSymbols
    ? model.themes.filter((item) => item.symbols.some((symbol) => focusSymbols.has(symbol)))
    : discoveryThemes
      ? model.themes.filter((item) => discoveryThemes.has(item.name))
      : ["theme-link", "source-count", "full-chain"].includes(variant)
        ? model.themes.filter((item) => item.symbols.length > 0)
        : model.themes;
  const linkedSymbols = [...new Set(news.flatMap((item) => item.symbols))];
  const hasEvidenceEdges = news.some((item) => item.symbols.length > 0 && item.themes.length > 0)
    && themes.some((theme) => theme.symbols.length > 0);
  if (!hasEvidenceEdges) return <Empty>当前筛选没有同时具备资讯、题材和 A 股关联的可验证证据，已收紧为空态。</Empty>;
  return <div className="evidence-map"><div className="evidence-column"><small>原始资讯</small>{news.slice(0, 5).map((item) => <span key={item.event_id}>{item.headline}</span>)}</div><Network size={28} /><div className="evidence-column"><small>题材归因</small>{themes.slice(0, 6).map((theme) => <span key={theme.name}>{theme.name}</span>)}</div><Network size={28} /><div className="evidence-column evidence-stock-column"><small>关联 A 股</small>{linkedSymbols.slice(0, 8).map((symbol) => { const name = stockNameForSymbol(model, symbol); return onOpenAShare ? <button type="button" key={symbol} aria-label={`查看 ${symbol} ${name}`} onClick={() => onOpenAShare(symbol)}>{name}<small>{symbol}</small></button> : <span key={symbol}>{name}<small>{symbol}</small></span>; })}</div></div>;
}

function flowAmount(value: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  return `${parsed > 0 ? "+" : ""}${parsed.toFixed(2)}亿`;
}

function LargeOrderFlowBoard({ data, onOpenAShare }: { data: MarketOverviewResponse; onOpenAShare?: (symbol: string) => void }) {
  const rows = data.large_order_flows ?? [];
  if (!rows.length) return null;
  const maxAbs = Math.max(...rows.map((item) => Math.abs(Number(item.main_net_yi))), 0.01);
  return <div className="large-order-flow-board">
    <header><div><b>真实大单方向</b><small>真实资金流缓存样本 {rows.length} 只</small></div><span>单位：亿元</span></header>
    <div className="large-order-zero-axis" aria-label="真实大单净流入零轴图">
      {rows.slice(0, 16).map((item) => {
        const mainNet = Number(item.main_net_yi);
        const width = Math.min(50, Math.abs(mainNet) / maxAbs * 50);
        return <article key={item.symbol} className={tone(mainNet)} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(item.symbol) : undefined, `查看 ${item.symbol} ${item.name}`)}>
          <span>{onOpenAShare ? <button type="button" aria-label={`查看 ${item.symbol} ${item.name}`} onClick={(event) => { event.stopPropagation(); onOpenAShare(item.symbol); }}><b>{item.name}</b><small>{item.symbol}</small></button> : <><b>{item.name}</b><small>{item.symbol}</small></>}</span>
          <div className="large-order-zero-axis-track"><i className={mainNet >= 0 ? "inflow" : "outflow"} style={{ "--flow-width": `${width}%` } as CSSProperties} /></div>
          <strong>{flowAmount(item.main_net_yi)}</strong>
          <small>大单 {flowAmount(item.large_net_yi)} · 超大单 {flowAmount(item.super_net_yi)}</small>
        </article>;
      })}
    </div>
    <footer>来源：东财资金流原始大单/超大单字段 · 交易日 {rows[0]?.latest_trade_date} · 不是成交额代理</footer>
  </div>;
}

function SectorFundFlowMotion({ data }: { data: MarketOverviewResponse }) {
  const points = data.sector_fund_flow ?? [];
  if (!points.length) return null;
  const grouped = new Map<string, typeof points>();
  for (const point of points) {
    const current = grouped.get(point.sector_code) ?? [];
    current.push(point);
    grouped.set(point.sector_code, current);
  }
  const groups = [...grouped.values()].map((items) => (
    [...items].sort((left, right) => Date.parse(left.observed_at) - Date.parse(right.observed_at))
  ));
  const latest = groups.map((items) => items[items.length - 1]).filter(Boolean);
  const option: EChartsOption = {
    animationDurationUpdate: 280,
    textStyle: { color: chartTheme.textColor, fontFamily: chartTheme.fontFamily },
    grid: { left: 64, right: 24, top: 34, bottom: 46 },
    tooltip: {
      trigger: "axis",
      backgroundColor: chartTheme.tooltipBackgroundColor,
      borderColor: chartTheme.liveColor,
      textStyle: { color: chartTheme.textColor, fontSize: 13 },
      valueFormatter: (value) => `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(2)}亿`,
    },
    legend: { top: 2, textStyle: { color: chartTheme.mutedTextColor, fontSize: 12 } },
    xAxis: {
      type: "time",
      axisLabel: { color: chartTheme.mutedTextColor, formatter: "{HH}:{mm}" },
      axisLine: { lineStyle: { color: chartTheme.gridColor } },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: "亿元",
      nameTextStyle: { color: chartTheme.mutedTextColor },
      axisLabel: { color: chartTheme.mutedTextColor },
      splitLine: { lineStyle: { color: chartTheme.gridColor } },
    },
    series: groups.map((items, groupIndex) => {
      const last = items[items.length - 1];
      const color = sectorColor(last.sector_code, groupIndex);
      return {
        name: last.sector_name,
        type: "line",
        showSymbol: items.length < 8,
        symbolSize: 7,
        smooth: 0.22,
        connectNulls: false,
        lineStyle: { width: 2, color },
        itemStyle: { color },
        emphasis: { focus: "series" },
        data: items.map((item) => [item.observed_at, Number(item.main_net_yi)]),
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { color: chartTheme.unavailableColor, type: "dashed", width: 1 },
          data: [{ yAxis: 0 }],
        },
      };
    }),
  };
  const sampleCount = data.data_scope?.sector_fund_flow_sample_count ?? groups.length;
  const snapshotCount = data.data_scope?.sector_fund_flow_snapshot_count ?? Math.max(...groups.map((items) => items.length), 0);
  const latestObservedAt = latest.reduce((current, item) => (
    !current || Date.parse(item.observed_at) > Date.parse(current) ? item.observed_at : current
  ), "");
  const stale = latest.some((item) => item.quality === "stale");
  return <div className="sector-fund-flow-motion">
    <header>
      <div><b>板块主力净流入轨迹</b><small>{sampleCount} 个板块 · {snapshotCount} 次真实采样</small></div>
      <span className={stale ? "stale" : "ready"}>{stale ? "缓存待刷新" : "动态监测"}</span>
    </header>
    <div className="sector-fund-flow-chart"><QuantChart option={option} ariaLabel="板块主力净流入时间序列" /></div>
    <div className="sector-fund-flow-latest">
      {latest.map((item, index) => {
        const color = sectorColor(item.sector_code, index);
        return <article key={item.sector_code} className={tone(Number(item.main_net_yi))} data-sector-color={color} style={{ "--sector-color": color } as CSSProperties}>
        <span><b><i className="sector-flow-swatch" style={{ backgroundColor: color }} aria-hidden="true" />{item.sector_name}</b><small>{item.sector_code}</small></span>
        <strong>{flowAmount(item.main_net_yi)}</strong>
        <small>大单 {item.large_net_yi === null ? "--" : flowAmount(item.large_net_yi)} · 超大单 {item.super_net_yi === null ? "--" : flowAmount(item.super_net_yi)}</small>
      </article>;
      })}
    </div>
    <footer>来源：东财板块资金流原始字段 · 最新采样 {latestObservedAt ? timeLabel(latestObservedAt) : "时间未知"} · 板块色区分板块 · 红色流入 / 绿色流出 · 不补空点</footer>
  </div>;
}

function CapitalAudit({ variant, data, onOpenAShare }: { variant: string; data: MarketOverviewResponse; onOpenAShare?: (symbol: string) => void }) {
  if (variant === "large-order" && (data.large_order_flows?.length ?? 0) > 0) return <LargeOrderFlowBoard data={data} onOpenAShare={onOpenAShare} />;
  if (variant === "sector-flow" && (data.sector_fund_flow?.length ?? 0) > 0) return <SectorFundFlowMotion data={data} />;
  const seat = ["seat-required", "seat-flow"].includes(variant);
  const sector = variant === "sector-flow";
  const title = seat ? "当前接口未提供龙虎榜席位" : sector ? "当前接口未提供板块真实资金流" : "当前接口未提供真实大单净流入";
  const fields = seat ? ["上榜日期", "营业部席位", "买入额", "卖出额", "净额"] : sector ? ["板块净流入", "流入时间序列", "主买方向", "资金持续性"] : ["逐笔方向", "大单阈值", "买入额", "卖出额", "净流入"];
  return <div className="capital-audit">
    <div className="capital-audit-summary"><ShieldAlert size={28} /><span><small>专有字段状态</small><h4>{title}</h4><p>{seat ? "成交额不能替代席位买卖。" : sector ? "板块成交额不能替代资金净流入。" : "高成交额不能替代主力买入。"}</p></span></div>
    <div className="capital-audit-fields"><b>待接字段</b>{fields.map((field) => <span key={field}><XCircle size={14} />{field}</span>)}</div>
    <footer>专有字段接入前保持不可用，不生成代理结论。</footer>
  </div>;
}

function DataAudit({ data, definition, variant }: { data: MarketOverviewResponse; definition: WorkspaceDefinition; variant: string }) {
  const coverage = data.market_data.universe_count > 0 ? data.market_data.quote_count / data.market_data.universe_count * 100 : null;
  const evidenceReady = (item: WorkspaceDefinition["requiredEvidence"][number]) => {
    if (item === "realtime-quotes") return data.market_data.quote_count > 0;
    if (item === "local-news") return data.live_feed.length > 0 || data.anomalies.length > 0;
    if (item === "sector-membership") return data.sectors.length > 0;
    if (item === "daily-history-100" || item === "daily-history-previous") return Boolean(data.review && data.review.history_ready_count > 0);
    if (item === "dragon-tiger-seats") return hasDragonTigerEvidence(data.review);
    if (item === "sector-capital-flow") return (data.sector_fund_flow?.length ?? 0) > 0;
    if (item === "large-order-flow") return (data.large_order_flows?.length ?? 0) > 0;
    return false;
  };
  const missing = definition.requiredEvidence.filter((item) => !evidenceReady(item));
  const available = [
    data.market_data.quote_count > 0 ? "实时量价" : null,
    data.sectors.length > 0 ? "板块" : null,
    (data.sector_fund_flow?.length ?? 0) > 0 ? "板块资金序列" : null,
    data.live_feed.length > 0 || data.anomalies.length > 0 ? "本地资讯" : null,
  ].filter((item): item is string => item !== null);
  const labels: Record<string, string> = {
    "order-book": "逐笔委托队列", "daily-history-100": "100 日日线", "daily-history-previous": "上一交易日日线",
    "dragon-tiger-seats": "龙虎榜席位", "large-order-flow": "真实大单流", "sector-capital-flow": "板块净流入序列",
  };
  return <div className="data-audit-grid">
    <article><Database /><span><small>行情主源</small><b>{data.market_data.source === "tdx-local-rpc" ? "本地通达信" : data.market_data.source}</b></span></article>
    <article><Activity /><span><small>行情覆盖</small><b>{coverage === null ? "--" : `${coverage.toFixed(1)}%`}</b></span></article>
    <article><CheckCircle2 /><span><small>当前可用</small><b>{available.length ? available.join(" / ") : "暂无已验证字段"}</b></span></article>
    <article className={missing.length ? "missing" : "ready"}>{missing.length ? <AlertTriangle /> : <CheckCircle2 />}<span><small>证据缺口</small><b>{missing.map((item) => labels[item] ?? item).join(" / ") || "本页所需字段已连接"}</b></span></article>
    <p>{variant.includes("iwencai") || variant === "not-iwencai" ? "这里执行本地确定性规则，没有调用问财官方语义接口。" : definition.truthBoundary}</p>
  </div>;
}

function StrategyRoute({ data }: { data: MarketOverviewResponse }) {
  const regime = data.regime;
  return <div className="strategy-route-block"><header><TrendingUp size={22} /><div><small>当前市场风格</small><b>{regime?.regime ?? "待确认"}</b></div><strong>{regime ? `MarketCoef ${Number(regime.market_coef).toFixed(1)}` : "--"}</strong></header><section><div><small>适用策略</small>{regime?.suitable_strategies.map((item) => <span key={item}>{item}</span>) || <span>等待风格识别</span>}</div><div className="avoid"><small>避免策略</small>{regime?.avoid_strategies.map((item) => <span key={item}>{item}</span>) || <span>等待风险因子</span>}</div></section></div>;
}

function StockInspector({ model, onOpenAShare }: { model: WorkspaceMarketModel; onOpenAShare?: (symbol: string) => void }) {
  const stock = model.stocks[0];
  if (!stock) return <Empty>当前代表股票集合为空，请在个股观察中搜索完整股票目录。</Empty>;
  return <div className="stock-inspector"><header><div><StockName stock={stock} onOpenAShare={onOpenAShare} /><span>{stock.symbol} · {stateLabel(stock)}</span></div><strong className={tone(stock.change)}>{signedPercent(stock.change)}</strong></header><div>{[["现价", stock.price], ["开盘", stock.open], ["最高", stock.high], ["最低", stock.low], ["昨收", stock.previous_close], ["成交额", optionalValue(stock.amount, "亿")], ["振幅", optionalValue(stock.amplitude, "%")], ["收盘位置", optionalValue(stock.closePosition, "%")]].map(([label, value]) => <article key={label}><small>{label}</small><b>{value}</b></article>)}</div><footer>{stock.themes.map((theme) => <span key={theme}>{theme}</span>)}</footer></div>;
}

function IndustryMap({ model, onOpenAShare }: { model: WorkspaceMarketModel; onOpenAShare?: (symbol: string) => void }) {
  if (!model.themes.length) return <Empty>当前产业资料没有形成可验证的主题与 A 股关联。</Empty>;
  return <div className="industry-map"><div className="industry-core"><Layers3 /><b>产业主题</b><strong>{model.themes.length}</strong></div>{model.themes.slice(0, 10).map((theme, index) => <article key={theme.name} className={`branch-${index % 2}`}><span>{theme.name}</span><small>{theme.evidenceCount} 条资料</small><p>{theme.symbols.length ? theme.symbols.slice(0, 5).map((symbol) => { const name = stockNameForSymbol(model, symbol); return <span key={symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(symbol) : undefined, `查看 ${symbol} ${name}`)}>{name}<small>{symbol}</small></span>; }) : "待关联公司"}</p></article>)}</div>;
}

function RiskBoard({ model, variant, onOpenAShare }: { model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  if (variant === "trend-failure") return <Empty>新高趋势逐股结果尚未由当前复盘接口返回，暂不生成失效清单。</Empty>;
  const stocks = variant === "crowding" ? [...model.stocks].filter((stock) => stock.themes.length >= 2).sort((a, b) => b.themes.length - a.themes.length)
    : variant === "opening-risk" ? model.stocks.filter((stock) => (known(stock.gap) && known(stock.change)) && ((stock.gap ?? 0) >= 2 && (stock.change ?? 0) < (stock.gap ?? 0) - 2 || (stock.gap ?? 0) <= -2 && (stock.change ?? 0) < 0))
    : variant === "strict-down" ? stocksForVariant(model, "strict-down")
    : variant === "promotion-risk" ? model.stocks.filter((stock) => stock.state === "broken_limit_up" || (known(stock.closePosition) && stock.closePosition < 25))
    : variant === "auction-failure" ? model.stocks.filter((stock) => known(stock.gap) && known(stock.change) && stock.gap > 0 && stock.change < stock.gap - 2)
    : model.stocks.filter((stock) => stock.state === "broken_limit_up" || stock.state === "limit_down" || (known(stock.change) && stock.change < -3));
  return <StockTable stocks={stocks} onOpenAShare={onOpenAShare} mode="risk" />;
}

function HistoricalRankingNotice({ variant }: { variant: string }) {
  const message = variant === "verified-only"
    ? "100 日新高逐股结果尚未由当前复盘接口返回。"
    : variant === "previous-only"
      ? "上一交易日涨停反馈逐股结果尚未由当前复盘接口返回。"
      : "区间收益逐股结果需要先选择明确的起止日期。";
  return <Empty>{message} 页面不会用当前代表股票快照代替历史结果。</Empty>;
}

export function WorkspaceBlockView({ block, definition, data, model, onOpenAShare, onOpenCompanyResearch, onOpenQuantAnalysis }: BlockProps) {
  let content: ReactNode;
  const actions = { onOpenAShare, onOpenCompanyResearch, onOpenQuantAnalysis };
  switch (block.kind) {
    case "market-pulse": content = <MarketPulse data={data} model={model} variant={block.variant} actions={actions} />; break;
    case "event-timeline": content = <EventTimeline model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "news-wire": content = <NewsWire model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "auction-gap": content = <AuctionGap model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "auction-gates": content = <AuctionGates model={model} />; break;
    case "stock-ranking": content = ["verified-only", "previous-only"].includes(block.variant)
      ? <HistoricalRankingTable data={data} variant={block.variant} onOpenAShare={onOpenAShare} />
      : block.variant === "interval-return"
        ? <HistoricalRankingNotice variant={block.variant} />
        : <StockTable stocks={stocksForVariant(model, block.variant)} onOpenAShare={onOpenAShare} mode={block.variant.includes("gap") || block.variant.includes("auction") ? "auction" : "default"} />; break;
    case "stock-matrix": content = <StockMatrix model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "stock-inspector": content = <StockInspector model={model} onOpenAShare={onOpenAShare} />; break;
    case "sector-heatmap": content = <SectorHeatmap model={model} variant={block.variant} />; break;
    case "sector-quadrant": content = <SectorQuadrant model={model} variant={block.variant} />; break;
    case "sector-members": content = <SectorMembers data={data} model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "theme-atlas": content = <ThemeAtlas model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "theme-matrix": content = <ThemeMatrix model={model} onOpenAShare={onOpenAShare} />; break;
    case "industry-map": content = <IndustryMap model={model} onOpenAShare={onOpenAShare} />; break;
    case "limit-ecology": content = <LimitEcology data={data} model={model} variant={block.variant} actions={actions} />; break;
    case "limit-board": content = block.variant === "sector-limit" ? <SectorLimitBoard data={data} model={model} onOpenAShare={onOpenAShare} /> : <StockTable stocks={stocksForVariant(model, "strict-limit")} onOpenAShare={onOpenAShare} />; break;
    case "failure-board": content = <StockTable stocks={stocksForVariant(model, "strict-broken")} onOpenAShare={onOpenAShare} mode="failure" />; break;
    case "height-pyramid": content = <HeightPyramid data={data} actions={actions} />; break;
    case "promotion-funnel": content = <PromotionFunnel model={model} actions={actions} />; break;
    case "leader-lanes": content = <LeaderLanes model={model} onOpenAShare={onOpenAShare} />; break;
    case "risk-board": content = <RiskBoard model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "distribution": content = <Distribution data={data} model={model} variant={block.variant} actions={actions} />; break;
    case "seven-rankings": content = <SevenRankings model={model} onOpenAShare={onOpenAShare} />; break;
    case "statistics-pivot": content = <StatisticsPivot data={data} model={model} variant={block.variant} actions={actions} />; break;
    case "event-calendar": content = <EventCalendar data={data} model={model} onOpenAShare={onOpenAShare} />; break;
    case "review-columns": content = <ReviewColumns model={model} actions={actions} />; break;
    case "rule-gates": content = <RuleGates data={data} model={model} variant={block.variant} />; break;
    case "evidence-map": content = <EvidenceMap model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "capital-audit": content = <CapitalAudit variant={block.variant} data={data} onOpenAShare={onOpenAShare} />; break;
    case "history-audit": content = <HistoryAudit data={data} variant={block.variant} />; break;
    case "data-audit": content = <DataAudit data={data} definition={definition} variant={block.variant} />; break;
    case "strategy-route": content = <StrategyRoute data={data} />; break;
    case "review-summary": content = <ReviewSummary data={data} variant={block.variant} actions={actions} />; break;
    case "limit-ladder": content = <LimitLadder data={data} onOpenAShare={onOpenAShare} />; break;
    case "first-board-table": content = <FirstBoardTable data={data} onOpenAShare={onOpenAShare} />; break;
    case "sector-performance": content = <SectorPerformance data={data} model={model} />; break;
    case "breakout-table": content = <BreakoutTable data={data} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "dragon-tiger-board": content = <DragonTigerBoard data={data} onOpenAShare={onOpenAShare} />; break;
    case "seat-tracker": content = <SeatTracker data={data} actions={actions} />; break;
    case "seat-direction": content = <SeatDirection data={data} actions={actions} />; break;
    default: content = <Empty>该功能区块尚未实现，构建测试应阻止此状态进入便携版。</Empty>;
  }
  return <Frame block={block}>{content}</Frame>;
}
