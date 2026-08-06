import {
  Activity, AlertTriangle, CalendarDays, CheckCircle2, Database,
  FileSearch, Layers3, Network, ShieldAlert, TrendingUp, XCircle,
} from "lucide-react";
import { useState, type CSSProperties, type ReactNode } from "react";

import type { MarketOverviewResponse, MarketReviewStock } from "../types";
import { interactiveTargetProps } from "../interactiveTarget";
import type { WorkspaceBlock, WorkspaceDefinition } from "./workspaceTypes";
import { hasDragonTigerEvidence } from "./workspaceEvidence";
import {
  numberValue, signedPercent, stocksForVariant,
  type DerivedStock, type WorkspaceMarketModel,
} from "./workspaceSelectors";

type BlockProps = {
  block: WorkspaceBlock;
  definition: WorkspaceDefinition;
  data: MarketOverviewResponse;
  model: WorkspaceMarketModel;
  onOpenAShare?: (symbol: string) => void;
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

function MarketPulse({ data }: { data: MarketOverviewResponse }) {
  const cards = [
    ["市场情绪", data.sentiment.score === null ? "--" : data.sentiment.score, data.sentiment.band],
    ["上涨 / 下跌", `${data.breadth.rising_count} / ${data.breadth.falling_count}`, `${data.breadth.valid_count} 只有效`],
    ["涨停 / 跌停", `${data.limit_ecology.limit_up_count} / ${data.limit_ecology.limit_down_count}`, `炸板 ${data.limit_ecology.broken_limit_up_count}`],
    ["封板率", data.limit_ecology.seal_rate_percent ? `${data.limit_ecology.seal_rate_percent}%` : "--", "涨停 / 触板"],
    ["成交热度", data.liquidity.relative_amount ? `${data.liquidity.relative_amount}x` : "--", data.liquidity.total_amount_yi ? `${data.liquidity.total_amount_yi}亿` : "基准不足"],
    ["市场风格", data.regime?.regime ?? "待确认", data.regime ? `系数 ${Number(data.regime.market_coef).toFixed(1)}` : "因子不足"],
  ];
  return <div className="distinct-metric-deck">{cards.map(([label, value, detail]) => <article key={label}><span>{label}</span><b>{value}</b><small>{detail}</small></article>)}</div>;
}

function EventTimeline({ model, variant }: { model: WorkspaceMarketModel; variant: string }) {
  const events = [...model.anomalies].sort((a, b) => {
    if (["voice-priority", "alert-priority"].includes(variant)) {
      const priority = { negative: 0, uncertain: 1, positive: 2, neutral: 3 } as const;
      return priority[a.direction] - priority[b.direction] || b.symbols.length - a.symbols.length;
    }
    return new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime();
  });
  if (!events.length) return <Empty>本地异动库当前没有已关联 A 股的事件。</Empty>;
  return <ol className="distinct-timeline">{events.slice(0, 18).map((item) => <li key={item.anomaly_id} className={`direction-${item.direction}`}>
    <time>{timeLabel(item.occurred_at)}</time><i /><div><b>{item.label}</b><p>{item.headline}</p><small>{item.themes.join(" / ") || "未归入题材"} · {item.symbols.join("、") || "未关联股票"}</small></div>
  </li>)}</ol>;
}

function NewsWire({ model, variant }: { model: WorkspaceMarketModel; variant: string }) {
  const popularSymbols = new Set(stocksForVariant(model, "attention-score").slice(0, 10).map((item) => item.symbol));
  const anomalySymbols = new Set(model.anomalies.flatMap((item) => item.symbols));
  const events = variant === "popular-evidence" ? model.news.filter((item) => item.symbols.some((symbol) => popularSymbols.has(symbol)))
    : ["voice-source", "stock-anomaly-news"].includes(variant) ? model.news.filter((item) => item.symbols.some((symbol) => anomalySymbols.has(symbol)))
    : model.news;
  if (!events.length) return <Empty>本地新闻库没有满足本功能关联条件的 A 股资讯。</Empty>;
  return <div className="distinct-news-wire">{events.slice(0, 16).map((item) => <article key={item.event_id}>
    <div><time>{timeLabel(item.occurred_at)}</time><span className={item.review_state === "verified" ? "verified" : "pending"}>{item.review_state}</span></div>
    <h4>{item.headline}</h4>{item.summary && <p>{item.summary}</p>}
    <footer>{item.themes.map((theme) => <span key={theme}>{theme}</span>)}<small>{item.source}</small></footer>
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

function SectorQuadrant({ model }: { model: WorkspaceMarketModel }) {
  const sectors = model.sectors.filter((sector) => known(sector.change) && known(sector.breadthPercent));
  if (!sectors.length) return <Empty>缺少板块涨幅和上涨家数，无法生成四象限。</Empty>;
  return <div className="sector-quadrant"><span className="axis-y">强度</span><span className="axis-x">广度</span>{sectors.slice(0, 16).map((sector) => <i key={sector.sector_id} title={`${sector.name} ${signedPercent(sector.change)}`} style={{ left: `${Math.max(5, Math.min(95, sector.breadthPercent ?? 50))}%`, bottom: `${Math.max(5, Math.min(95, 50 + (sector.change ?? 0) * 7))}%` }}><b>{sector.name}</b></i>)}</div>;
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

function ThemeAtlas({ model, variant }: { model: WorkspaceMarketModel; variant: string }) {
  const themes = ["anomaly-theme"].includes(variant) ? model.themes.filter((item) => item.anomalyCount > 0).sort((a, b) => b.anomalyCount - a.anomalyCount)
    : ["evidence-growth", "ai-evidence"].includes(variant) ? model.themes.filter((item) => item.evidenceCount >= 2).sort((a, b) => b.evidenceCount - a.evidenceCount)
    : ["broadcast-tags", "industry-docs"].includes(variant) ? model.themes.filter((item) => item.newsCount > 0).sort((a, b) => b.newsCount - a.newsCount)
    : variant === "opening-theme" ? [...model.themes].sort((a, b) => new Date(b.latestAt).getTime() - new Date(a.latestAt).getTime())
    : model.themes;
  if (!themes.length) return <Empty>本地新闻和异动中没有满足本功能条件的可追溯题材。</Empty>;
  return <div className="theme-atlas">{themes.slice(0, 24).map((theme, index) => <article key={theme.name} className={index < 3 ? "hot" : ""}>
    <header><b>{theme.name}</b><strong>{theme.evidenceCount}</strong></header><p>{theme.symbols.slice(0, 6).join(" · ") || "未关联股票"}</p>
    <footer><span>新闻 {theme.newsCount}</span><span>异动 {theme.anomalyCount}</span><time>{timeLabel(theme.latestAt)}</time></footer>
  </article>)}</div>;
}

function ThemeMatrix({ model }: { model: WorkspaceMarketModel }) {
  const stocks = stocksForVariant(model, "theme-count").filter((item) => item.themes.length > 0).slice(0, 14);
  const themes = model.themes.slice(0, 8);
  if (!stocks.length || !themes.length) return <Empty>当前没有同时具备股票代码与题材标签的证据。</Empty>;
  return <div className="theme-overlap-matrix"><div className="matrix-head"><span>股票</span>{themes.map((theme) => <b key={theme.name}>{theme.name}</b>)}</div>{stocks.map((stock) => <div key={stock.symbol}><span>{stock.name}<small>{stock.symbol}</small></span>{themes.map((theme) => <i key={theme.name} className={stock.themes.includes(theme.name) ? "hit" : ""}>{stock.themes.includes(theme.name) ? "●" : "·"}</i>)}</div>)}</div>;
}

function LimitEcology({ data }: { data: MarketOverviewResponse }) {
  const touched = data.limit_ecology.limit_up_count + data.limit_ecology.broken_limit_up_count;
  return <div className="limit-ecology-deck">
    <article className="sealed"><span>已封涨停</span><b>{data.limit_ecology.limit_up_count}</b><small>严格现价状态</small></article>
    <article className="broken"><span>触板未封</span><b>{data.limit_ecology.broken_limit_up_count}</b><small>最高价触板</small></article>
    <article className="down"><span>当前跌停</span><b>{data.limit_ecology.limit_down_count}</b><small>风险样本</small></article>
    <article><span>触板合计</span><b>{touched}</b><small>涨停 + 炸板</small></article>
    <article><span>封板率</span><b>{data.limit_ecology.seal_rate_percent ? `${data.limit_ecology.seal_rate_percent}%` : "--"}</b><small>已封 / 触板</small></article>
  </div>;
}

function reviewDate(data: MarketOverviewResponse): string {
  return data.review?.latest_trade_date ?? "交易日不可用";
}

function optionalValue(value: string | number | null | undefined, suffix = ""): string {
  return value === null || value === undefined || value === "" ? "--" : `${value}${suffix}`;
}

function ReviewSummary({ data, variant }: { data: MarketOverviewResponse; variant: string }) {
  const review = data.review;
  if (!review) return <Empty>本地日线复盘尚未完成首次扫描。</Empty>;
  if (variant === "dragon-tiger" && !hasDragonTigerEvidence(review)) return <Empty>龙虎榜公开接口当前不可用，且本地没有可用的真实缓存。</Empty>;
  const coverage = review.universe_count > 0 ? review.history_ready_count / review.universe_count * 100 : null;
  const boardHeights = review.consecutive_limit_up.map((item) => item.board_count).filter((value): value is number => value !== null && Number.isFinite(value));
  const ladderTop = boardHeights.length ? Math.max(...boardHeights) : null;
  const coverageLabel = coverage === null ? "--" : `${coverage.toFixed(1)}%`;
  const rows = variant === "limit-ladder" ? [
    ["最高连板", ladderTop === null ? "--" : `${ladderTop}板`, "连续收盘涨停"],
    ["连板股票", review.consecutive_limit_up.length, "至少 2 板"],
    ["高度层级", new Set(review.consecutive_limit_up.map((item) => item.board_count)).size, "真实日线分组"],
    ["历史覆盖", coverageLabel, `${review.history_ready_count}/${review.universe_count}`],
  ] : variant === "first-board" ? [
    ["首板数量", review.first_limit_up.length, "上一日未涨停"],
    ["成交过亿", review.first_limit_up.filter((item) => { const value = numberValue(item.amount_yi); return value !== null && value >= 1; }).length, "日成交额"],
    ["平均涨幅", optionalValue(average(review.first_limit_up.map((item) => numberValue(item.change_percent)).filter((value): value is number => value !== null)), "%"), "最新交易日"],
    ["历史覆盖", coverageLabel, `${review.history_ready_count}/${review.universe_count}`],
  ] : variant === "dragon-tiger" ? [
    ["上榜股票", review.dragon_tiger.length, "公开榜单"],
    ["净买入", review.dragon_tiger.filter((item) => Number(item.net_amount_yi) > 0).length, "按公开净额"],
    ["席位明细", review.dragon_tiger.reduce((sum, item) => sum + item.seats.length, 0), "真实席位记录"],
    ["榜单日期", review.dragon_tiger[0]?.trade_date ?? "--", "缓存可追溯"],
  ] : (() => {
    const target = variant === "volume-breakout" ? review.volume_breakouts
      : variant === "previous-high" ? review.previous_high_breakouts : review.low_position_volume;
    return [
      ["规则命中", target.length, "严格筛选"],
      ["最大量能", optionalValue(maxNullable(target.map((item) => numberValue(item.volume_multiple)).filter((value): value is number => value !== null)), "x"), "相对前 5 日均量"],
      ["成交过亿", target.filter((item) => { const value = numberValue(item.amount_yi); return value !== null && value >= 1; }).length, "日成交额"],
      ["历史覆盖", coverageLabel, `${review.history_ready_count}/${review.universe_count}`],
    ];
  })();
  return <div className="review-summary-grid">{rows.map(([label, value, note], index) => { const parsed = numberValue(value); const meter = index === 3 ? coverage : parsed; return <article key={String(label)} data-state={meter === null ? "unavailable" : "ready"} style={{ "--meter": `${meter === null ? 0 : Math.min(100, Math.max(6, meter))}%` } as CSSProperties}><i /><span>{label}</span><b>{value}</b><small>{note}</small></article>; })}</div>;
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
  return <div className="breakout-review"><header>{variant === "volume-breakout" ? "收盘达到此前 60 日最高收盘 · 成交量 / 前 5 日均量 >= 1.8" : variant === "previous-high" ? "收盘突破此前 20 日最高价 · 成交量 / 前 5 日均量 >= 1.2" : "120 日区间位置 <= 30% · 成交量 / 前 5 日均量 >= 1.5"}</header><div className="distinct-table-scroll"><table className="distinct-table review-detail-table"><thead><tr><th>代码 / 名称</th><th>收盘</th><th>涨跌幅</th><th>量能倍数</th><th>成交额</th>{variant !== "low-position" && <th>参考前高</th>}{variant === "low-position" && <th>区间位置</th>}<th>窗口</th></tr></thead><tbody>{rows.map((item) => { const volume = numberValue(item.volume_multiple); return <tr key={item.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(item.symbol) : undefined, `查看 ${item.symbol} ${item.name}`)}><td><span>{item.symbol}<ReviewStockLink item={item} onOpenAShare={onOpenAShare} /></span></td><td>{optionalValue(item.close)}</td><td className={tone(numberValue(item.change_percent))}>{signedPercent(numberValue(item.change_percent))}</td><td><em className="volume-multiple">{volume === null ? "--" : `${volume.toFixed(2)}x`}</em></td><td>{optionalValue(item.amount_yi, "亿")}</td>{variant !== "low-position" && <td>{optionalValue(item.reference_high)}</td>}{variant === "low-position" && <td>{optionalValue(item.range_position_percent, "%")}</td>}<td>{optionalValue(item.window_days, "日")}</td></tr>; })}</tbody></table></div></div>;
}

function DragonTigerBoard({ data, onOpenAShare }: { data: MarketOverviewResponse; onOpenAShare?: (symbol: string) => void }) {
  const rows = data.review?.dragon_tiger ?? [];
  const [selectedSymbol, setSelectedSymbol] = useState(rows[0]?.symbol ?? "");
  if (!hasDragonTigerEvidence(data.review)) return <Empty>龙虎榜公开接口当前不可用，且本地没有可用的真实缓存。</Empty>;
  if (!rows.length) return <Empty>{reviewDate(data)} 公开龙虎榜没有上榜股票。</Empty>;
  const selected = rows.find((item) => item.symbol === selectedSymbol) ?? rows[0];
  const money = (value: string | null | undefined) => { const parsed = numberValue(value); return parsed === null ? "--" : `${parsed >= 0 ? "+" : ""}${parsed}亿`; };
  return <div className="dragon-tiger-workbench"><aside>{rows.map((item) => <button type="button" className={item.symbol === selected.symbol ? "active" : ""} key={`${item.trade_date}-${item.symbol}`} onClick={() => setSelectedSymbol(item.symbol)}><span><b>{item.name}</b><small>{item.symbol} · {item.trade_date}</small></span><strong className={tone(numberValue(item.net_amount_yi))}>{money(item.net_amount_yi)}</strong></button>)}</aside><section><header><div>{onOpenAShare ? <button type="button" onClick={() => onOpenAShare(selected.symbol)}>{selected.name} <small>{selected.symbol}</small></button> : <h4>{selected.name} <small>{selected.symbol}</small></h4>}<p>{selected.reason}</p></div><span><small>榜单净额</small><b className={tone(numberValue(selected.net_amount_yi))}>{money(selected.net_amount_yi)}</b></span></header><div className="dragon-tiger-totals"><article><small>买入额</small><b>{optionalValue(selected.buy_amount_yi, "亿")}</b></article><article><small>卖出额</small><b>{optionalValue(selected.sell_amount_yi, "亿")}</b></article><article><small>净额</small><b className={tone(numberValue(selected.net_amount_yi))}>{money(selected.net_amount_yi)}</b></article><article><small>涨跌幅</small><b className={tone(numberValue(selected.change_percent))}>{signedPercent(numberValue(selected.change_percent))}</b></article></div>{selected.seats.length ? <div className="distinct-table-scroll"><table className="distinct-table"><thead><tr><th>方向</th><th>席位</th><th>买入额</th><th>卖出额</th><th>净额</th></tr></thead><tbody>{selected.seats.map((seat, index) => <tr key={`${seat.seat_name}-${index}`}><td>{seat.direction === "buy" ? "买入" : seat.direction === "sell" ? "卖出" : "双向"}</td><td>{seat.seat_name}</td><td>{optionalValue(seat.buy_amount_yi, "亿")}</td><td>{optionalValue(seat.sell_amount_yi, "亿")}</td><td className={tone(numberValue(seat.net_amount_yi))}>{money(seat.net_amount_yi)}</td></tr>)}</tbody></table></div> : <Empty>榜单股票真实可用，但席位明细接口未返回记录。</Empty>}</section></div>;
}

function SeatTracker({ data }: { data: MarketOverviewResponse }) {
  const seats = data.review?.dragon_tiger.flatMap((stock) => stock.seats.map((seat) => ({ ...seat, stockName: stock.name }))) ?? [];
  if (!hasDragonTigerEvidence(data.review)) return <Empty>龙虎榜公开接口当前不可用，且本地没有可追溯缓存。</Empty>;
  if (!seats.length) return <Empty>{reviewDate(data)} 龙虎榜没有返回带名称和买卖金额的席位明细。</Empty>;
  const grouped = new Map<string, { buy: number; sell: number; net: number; symbols: Set<string> }>();
  seats.forEach((seat) => {
    const current = grouped.get(seat.seat_name) ?? { buy: 0, sell: 0, net: 0, symbols: new Set<string>() };
    const buy = numberValue(seat.buy_amount_yi);
    const sell = numberValue(seat.sell_amount_yi);
    const net = numberValue(seat.net_amount_yi);
    if (buy !== null) current.buy += buy;
    if (sell !== null) current.sell += sell;
    if (net !== null) current.net += net;
    current.symbols.add(seat.symbol);
    grouped.set(seat.seat_name, current);
  });
  const rows = [...grouped.entries()].sort((a, b) => Math.abs(b[1].net) - Math.abs(a[1].net));
  return <div className="distinct-table-scroll"><table className="distinct-table seat-tracker-table"><thead><tr><th>席位名称</th><th>涉及股票</th><th>买入额</th><th>卖出额</th><th>净额</th><th>方向</th></tr></thead><tbody>{rows.map(([name, row]) => <tr key={name}><td><b>{name}</b></td><td>{row.symbols.size}</td><td>{row.buy.toFixed(2)}亿</td><td>{row.sell.toFixed(2)}亿</td><td className={tone(row.net)}>{row.net >= 0 ? "+" : ""}{row.net.toFixed(2)}亿</td><td><span className={`seat-direction-tag ${tone(row.net)}`}>{row.net > 0 ? "净买入" : row.net < 0 ? "净卖出" : "买卖平衡"}</span></td></tr>)}</tbody></table></div>;
}

function SeatDirection({ data }: { data: MarketOverviewResponse }) {
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
  return <div className="seat-direction-dashboard">{groups.map(([label, rows, itemTone]) => {
    const net = rows.reduce((sum, item) => sum + Number(item.net_amount_yi), 0);
    const leader = [...rows].sort((a, b) => Math.abs(Number(b.net_amount_yi)) - Math.abs(Number(a.net_amount_yi)))[0];
    return <section key={label} className={itemTone}><header><span>{label}</span><b>{rows.length} 只</b></header><strong>{net >= 0 ? "+" : ""}{net.toFixed(2)}亿</strong><p>{leader ? `${leader.name} ${leader.symbol}` : "当前无记录"}</p><small>{leader ? `最大单股净额 ${Number(leader.net_amount_yi) >= 0 ? "+" : ""}${leader.net_amount_yi}亿` : "不生成替代数据"}</small></section>;
  })}</div>;
}

function HistoryAudit({ variant }: { variant: string }) {
  const labels = variant === "new-high" ? ["所需窗口", "100 个交易日", "验证结果", "等待日线覆盖"]
    : variant === "previous-limit" ? ["所需日期", "上一交易日", "反馈样本", "等待昨日涨停名单"]
    : variant === "consecutive-days" ? ["所需连续窗口", "至少 2 个交易日", "连板高度", "暂不可验证"]
    : ["统计区间", "需明确起止日", "有效样本", "等待历史窗口"];
  return <div className="history-audit"><AlertTriangle size={28} /><div><small>{labels[0]}</small><b>{labels[1]}</b></div><div><small>{labels[2]}</small><b>{labels[3]}</b></div><p>当前总览响应只含实时代表股票快照。页面不会用今日涨幅代替历史结论。</p></div>;
}

function HeightPyramid({ data }: { data: MarketOverviewResponse }) {
  if (!data.review) return <Empty>本地日线复盘尚未完成，不能用当前涨幅推断连板高度。</Empty>;
  const rows = data.review.consecutive_limit_up;
  if (!rows.length) return <Empty>{reviewDate(data)} 没有检测到连续 2 个交易日收盘涨停的股票。</Empty>;
  const heights = rows.map((item) => item.board_count).filter((value): value is number => value !== null && Number.isFinite(value));
  if (!heights.length) return <Empty>{reviewDate(data)} 连板记录存在，但连板高度字段不可用。</Empty>;
  const max = Math.max(...heights);
  return <div className="height-pyramid">{Array.from({ length: Math.max(1, max - 1) }, (_, index) => max - index).map((level, index) => {
    const count = rows.filter((item) => item.board_count === level).length;
    return <div key={level} style={{ width: `${Math.min(96, 38 + index * 12)}%` }}><b>{level} 板</b><span>{count}</span><small>{count ? "真实日线验证" : "该高度为空"}</small></div>;
  })}</div>;
}

function PromotionFunnel({ model }: { model: WorkspaceMarketModel }) {
  const active = model.stocks.length;
  const strong = model.stocks.filter((stock) => known(stock.change) && stock.change > 5).length;
  const sealed = model.stocks.filter((stock) => stock.state === "limit_up").length;
  const evidenced = model.stocks.filter((stock) => stock.themes.length > 0).length;
  const stages = [["代表样本", active], ["涨幅 > 5%", strong], ["当前封板", sealed], ["具备题材证据", evidenced]] as const;
  return <div className="promotion-funnel">{stages.map(([label, value], index) => <article key={label} style={{ width: `${100 - index * 16}%` }}><span>{index + 1}</span><b>{label}</b><strong>{value}</strong></article>)}</div>;
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

function Distribution({ data, model, variant }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string }) {
  if (["selected-window", "distance-high", "feedback"].includes(variant)) return <HistoryAudit variant={variant} />;
  const bins = [
    ["跌幅 > 7%", model.stocks.filter((stock) => known(stock.change) && stock.change <= -7).length, "down"],
    ["-7% ~ 0", model.stocks.filter((stock) => known(stock.change) && stock.change > -7 && stock.change < 0).length, "down"],
    ["平盘", model.stocks.filter((stock) => known(stock.change) && stock.change === 0).length, "flat"],
    ["0 ~ 7%", model.stocks.filter((stock) => known(stock.change) && stock.change > 0 && stock.change < 7).length, "up"],
    ["涨幅 >= 7%", model.stocks.filter((stock) => known(stock.change) && stock.change >= 7).length, "up"],
  ];
  const max = Math.max(1, ...bins.map((item) => Number(item[1])));
  return <div className="distribution-bars">{bins.map(([label, value, itemTone]) => <article key={String(label)}><span>{label}</span><div className={String(itemTone)}><i style={{ width: `${Number(value) / max * 100}%` }} /></div><b>{value}</b></article>)}<footer>全市场广度：上涨 {data.breadth.rising_count} / 下跌 {data.breadth.falling_count}；柱状分布仅覆盖接口代表股票。</footer></div>;
}

function SevenRankings({ model }: { model: WorkspaceMarketModel }) {
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
  return <div className="seven-rankings">{ranks.map(([label, stock], index) => <article key={label}><span>0{index + 1}</span><small>{label}榜首</small><b>{stock?.name ?? "暂无样本"}</b><em>{stock ? stock.symbol : "--"}</em><strong>{stock ? signedPercent(stock.change) : "--"}</strong></article>)}</div>;
}

function StatisticsPivot({ data, model, variant }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string }) {
  const rows = variant === "direction-theme-time" ? [
    ["正向异动", model.anomalies.filter((item) => item.direction === "positive").length, "本地异动库"],
    ["风险异动", model.anomalies.filter((item) => item.direction === "negative").length, "本地异动库"],
    ["待确认", model.anomalies.filter((item) => item.direction === "uncertain").length, "本地异动库"],
    ["关联题材", model.themes.length, "资讯与异动去重"],
  ] : [
    ["上涨家数", data.breadth.rising_count, "全市场快照"], ["下跌家数", data.breadth.falling_count, "全市场快照"],
    ["涨停家数", data.limit_ecology.limit_up_count, "严格现价"], ["炸板家数", data.limit_ecology.broken_limit_up_count, "触板未封"],
    ["板块样本", model.sectors.length, "本地板块"], ["A 股资讯", model.news.length, "已关联代码"],
  ];
  return <div className="statistics-pivot">{rows.map(([label, value, source]) => <article key={String(label)}><span>{label}</span><b>{value}</b><small>{source}</small></article>)}</div>;
}

function EventCalendar({ model }: { model: WorkspaceMarketModel }) {
  if (!model.news.length) return <Empty>没有带时间戳且已关联 A 股的本地资讯。</Empty>;
  const groups = new Map<string, typeof model.news>();
  model.news.forEach((item) => {
    const day = item.occurred_at.slice(0, 10);
    groups.set(day, [...(groups.get(day) ?? []), item]);
  });
  return <div className="event-calendar">{[...groups.entries()].map(([day, items]) => <section key={day}><header><CalendarDays size={18} /><div><b>{day}</b><small>{items.length} 项已入库事件</small></div></header>{items.slice(0, 8).map((item) => <article key={item.event_id}><time>{timeLabel(item.occurred_at).slice(-5)}</time><div><b>{item.headline}</b><small>{item.source} · {item.symbols.join("、")}</small></div></article>)}</section>)}</div>;
}

function ReviewColumns({ model }: { model: WorkspaceMarketModel }) {
  const columns = [
    ["封板", model.stocks.filter((stock) => stock.state === "limit_up"), "sealed"],
    ["炸板", model.stocks.filter((stock) => stock.state === "broken_limit_up"), "broken"],
    ["跌停", model.stocks.filter((stock) => stock.state === "limit_down"), "down"],
  ] as const;
  return <div className="review-columns">{columns.map(([label, stocks, className]) => <section key={label} className={className}><header><b>{label}</b><strong>{stocks.length}</strong></header>{stocks.slice(0, 10).map((stock) => <article key={stock.symbol}><span>{stock.name}<small>{stock.symbol}</small></span><b>{signedPercent(stock.change)}</b></article>)}{!stocks.length && <p>无严格记录</p>}</section>)}</div>;
}

function RuleGates({ data, model, variant }: { data: MarketOverviewResponse; model: WorkspaceMarketModel; variant: string }) {
  if (variant === "deterministic") return <AuctionGates model={model} />;
  const gates = variant === "next-day" ? [
    ["涨停当日不追买", true], ["次日只在触发后观察", true], ["炸板与跌停先降级", data.limit_ecology.broken_limit_up_count + data.limit_ecology.limit_down_count === 0],
  ] : variant === "leader-rules" ? [
    ["当前严格封板", data.limit_ecology.limit_up_count > 0], ["板块存在扩散", model.sectors.some((sector) => sector.limit_up_count >= 2)], ["资讯题材可追溯", model.themes.length > 0], ["历史连板已验证", false],
  ] : [
    ["行情覆盖 >= 80%", data.market_data.universe_count > 0 && data.market_data.quote_count / data.market_data.universe_count >= 0.8],
    ["市场风格已识别", Boolean(data.regime?.regime)], ["候选含真实行情", model.stocks.length > 0], ["题材证据可追溯", model.themes.length > 0],
  ];
  return <div className="vertical-gates">{gates.map(([label, pass], index) => <article key={String(label)} className={pass ? "pass" : "blocked"}><span>{index + 1}</span>{pass ? <CheckCircle2 /> : <XCircle />}<b>{label}</b><small>{pass ? "通过" : "阻断 / 待补证据"}</small></article>)}</div>;
}

function EvidenceMap({ model, variant }: { model: WorkspaceMarketModel; variant: string }) {
  const focusSymbols = variant === "alert-links" ? new Set(model.anomalies.filter((item) => item.direction === "negative").flatMap((item) => item.symbols))
    : variant === "stock-news" && model.stocks[0] ? new Set([model.stocks[0].symbol]) : null;
  const news = focusSymbols ? model.news.filter((item) => item.symbols.some((symbol) => focusSymbols.has(symbol))) : model.news;
  const themes = focusSymbols ? model.themes.filter((item) => item.symbols.some((symbol) => focusSymbols.has(symbol))) : model.themes;
  if (!news.length && !themes.length) return <Empty>没有满足本功能关联条件的新闻、题材与股票证据。</Empty>;
  return <div className="evidence-map"><div className="evidence-column"><small>原始资讯</small>{news.slice(0, 5).map((item) => <span key={item.event_id}>{item.headline}</span>)}</div><Network size={28} /><div className="evidence-column"><small>题材归因</small>{themes.slice(0, 6).map((theme) => <span key={theme.name}>{theme.name}</span>)}</div><Network size={28} /><div className="evidence-column"><small>A 股代码</small>{[...new Set(news.flatMap((item) => item.symbols))].slice(0, 8).map((symbol) => <span key={symbol}>{symbol}</span>)}</div></div>;
}

function CapitalAudit({ variant }: { variant: string }) {
  const seat = ["seat-required", "seat-flow"].includes(variant);
  const sector = variant === "sector-flow";
  const title = seat ? "当前接口未提供龙虎榜席位" : sector ? "当前接口未提供板块真实资金流" : "当前接口未提供真实大单净流入";
  const fields = seat ? ["上榜日期", "营业部席位", "买入额", "卖出额", "净额"] : sector ? ["板块净流入", "流入时间序列", "主买方向", "资金持续性"] : ["逐笔方向", "大单阈值", "买入额", "卖出额", "净流入"];
  return <div className="capital-audit"><ShieldAlert size={30} /><h4>{title}</h4><p>{seat ? "成交额不能替代席位买卖。" : sector ? "板块成交额不能替代资金净流入。" : "高成交额不能替代主力买入。"}</p><div>{fields.map((field) => <span key={field}><XCircle size={14} />{field}</span>)}</div><small>专有字段接入前保持不可用，不生成代理结论。</small></div>;
}

function DataAudit({ data, definition, variant }: { data: MarketOverviewResponse; definition: WorkspaceDefinition; variant: string }) {
  const coverage = data.market_data.universe_count > 0 ? data.market_data.quote_count / data.market_data.universe_count * 100 : null;
  const evidenceReady = (item: WorkspaceDefinition["requiredEvidence"][number]) => {
    if (item === "realtime-quotes") return data.market_data.quote_count > 0;
    if (item === "local-news") return data.live_feed.length > 0 || data.anomalies.length > 0;
    if (item === "sector-membership") return data.sectors.length > 0;
    if (item === "daily-history-100" || item === "daily-history-previous") return Boolean(data.review && data.review.history_ready_count > 0);
    if (item === "dragon-tiger-seats") return hasDragonTigerEvidence(data.review);
    return false;
  };
  const missing = definition.requiredEvidence.filter((item) => !evidenceReady(item));
  const available = [
    data.market_data.quote_count > 0 ? "实时量价" : null,
    data.sectors.length > 0 ? "板块" : null,
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

function IndustryMap({ model }: { model: WorkspaceMarketModel }) {
  if (!model.themes.length) return <Empty>当前产业资料没有形成可验证的主题与 A 股关联。</Empty>;
  return <div className="industry-map"><div className="industry-core"><Layers3 /><b>产业主题</b><strong>{model.themes.length}</strong></div>{model.themes.slice(0, 10).map((theme, index) => <article key={theme.name} className={`branch-${index % 2}`}><span>{theme.name}</span><small>{theme.evidenceCount} 条资料</small><p>{theme.symbols.slice(0, 5).join(" · ") || "待关联公司"}</p></article>)}</div>;
}

function RiskBoard({ model, variant, onOpenAShare }: { model: WorkspaceMarketModel; variant: string; onOpenAShare?: (symbol: string) => void }) {
  const stocks = variant === "strict-down" ? stocksForVariant(model, "strict-down")
    : variant === "promotion-risk" ? model.stocks.filter((stock) => stock.state === "broken_limit_up" || (known(stock.closePosition) && stock.closePosition < 25))
    : variant === "auction-failure" ? model.stocks.filter((stock) => known(stock.gap) && known(stock.change) && stock.gap > 0 && stock.change < stock.gap - 2)
    : model.stocks.filter((stock) => stock.state === "broken_limit_up" || stock.state === "limit_down" || (known(stock.change) && stock.change < -3));
  return <StockTable stocks={stocks} onOpenAShare={onOpenAShare} mode="risk" />;
}

export function WorkspaceBlockView({ block, definition, data, model, onOpenAShare }: BlockProps) {
  let content: ReactNode;
  switch (block.kind) {
    case "market-pulse": content = <MarketPulse data={data} />; break;
    case "event-timeline": content = <EventTimeline model={model} variant={block.variant} />; break;
    case "news-wire": content = <NewsWire model={model} variant={block.variant} />; break;
    case "auction-gap": content = <AuctionGap model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "auction-gates": content = <AuctionGates model={model} />; break;
    case "stock-ranking": content = <StockTable stocks={stocksForVariant(model, block.variant)} onOpenAShare={onOpenAShare} mode={block.variant.includes("gap") || block.variant.includes("auction") ? "auction" : "default"} />; break;
    case "stock-matrix": content = <StockMatrix model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "stock-inspector": content = <StockInspector model={model} onOpenAShare={onOpenAShare} />; break;
    case "sector-heatmap": content = <SectorHeatmap model={model} variant={block.variant} />; break;
    case "sector-quadrant": content = <SectorQuadrant model={model} />; break;
    case "sector-members": content = <SectorMembers data={data} model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "theme-atlas": content = <ThemeAtlas model={model} variant={block.variant} />; break;
    case "theme-matrix": content = <ThemeMatrix model={model} />; break;
    case "industry-map": content = <IndustryMap model={model} />; break;
    case "limit-ecology": content = <LimitEcology data={data} />; break;
    case "limit-board": content = block.variant === "sector-limit" ? <SectorLimitBoard data={data} model={model} onOpenAShare={onOpenAShare} /> : <StockTable stocks={stocksForVariant(model, "strict-limit")} onOpenAShare={onOpenAShare} />; break;
    case "failure-board": content = <StockTable stocks={stocksForVariant(model, "strict-broken")} onOpenAShare={onOpenAShare} mode="failure" />; break;
    case "height-pyramid": content = <HeightPyramid data={data} />; break;
    case "promotion-funnel": content = <PromotionFunnel model={model} />; break;
    case "leader-lanes": content = <LeaderLanes model={model} onOpenAShare={onOpenAShare} />; break;
    case "risk-board": content = <RiskBoard model={model} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "distribution": content = <Distribution data={data} model={model} variant={block.variant} />; break;
    case "seven-rankings": content = <SevenRankings model={model} />; break;
    case "statistics-pivot": content = <StatisticsPivot data={data} model={model} variant={block.variant} />; break;
    case "event-calendar": content = <EventCalendar model={model} />; break;
    case "review-columns": content = <ReviewColumns model={model} />; break;
    case "rule-gates": content = <RuleGates data={data} model={model} variant={block.variant} />; break;
    case "evidence-map": content = <EvidenceMap model={model} variant={block.variant} />; break;
    case "capital-audit": content = <CapitalAudit variant={block.variant} />; break;
    case "history-audit": content = <HistoryAudit variant={block.variant} />; break;
    case "data-audit": content = <DataAudit data={data} definition={definition} variant={block.variant} />; break;
    case "strategy-route": content = <StrategyRoute data={data} />; break;
    case "review-summary": content = <ReviewSummary data={data} variant={block.variant} />; break;
    case "limit-ladder": content = <LimitLadder data={data} onOpenAShare={onOpenAShare} />; break;
    case "first-board-table": content = <FirstBoardTable data={data} onOpenAShare={onOpenAShare} />; break;
    case "sector-performance": content = <SectorPerformance data={data} model={model} />; break;
    case "breakout-table": content = <BreakoutTable data={data} variant={block.variant} onOpenAShare={onOpenAShare} />; break;
    case "dragon-tiger-board": content = <DragonTigerBoard data={data} onOpenAShare={onOpenAShare} />; break;
    case "seat-tracker": content = <SeatTracker data={data} />; break;
    case "seat-direction": content = <SeatDirection data={data} />; break;
    default: content = <Empty>该功能区块尚未实现，构建测试应阻止此状态进入便携版。</Empty>;
  }
  return <Frame block={block}>{content}</Frame>;
}
