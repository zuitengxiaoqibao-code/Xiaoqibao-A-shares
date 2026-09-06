import type { MarketOverviewResponse } from "../types";
import { createMetricContract, type MetricContract } from "../../../shared/evidence/metricContract";
import type { MetricDrilldownSelection } from "./MetricDrilldown";
import { hasDragonTigerEvidence } from "./workspaceEvidence";
import { numberValue, type WorkspaceMarketModel } from "./workspaceSelectors";

export type InsightQuality = "ready" | "partial" | "unavailable";
export type InsightTone = "positive" | "warning" | "danger" | "neutral";
export type InsightBasis = "raw" | "derived" | "composite" | "unavailable";

export type WorkspaceInsight = {
  key: MetricKey;
  label: string;
  value: string;
  detail: string;
  quality: InsightQuality;
  tone: InsightTone;
  basis: InsightBasis;
  method?: string;
  drilldown?: MetricDrilldownSelection;
  contract?: MetricContract;
  icon: "pulse" | "news" | "theme" | "auction" | "limit" | "sector" | "history" | "seat" | "risk" | "data" | "stock";
};

type MetricKey =
  | "anomaly-total" | "anomaly-positive" | "anomaly-negative" | "anomaly-symbols"
  | "news-total" | "news-verified" | "news-symbols" | "latest-news"
  | "theme-total" | "top-theme" | "theme-symbols" | "theme-confluence"
  | "gap-up" | "gap-down" | "gap-recovery" | "auction-pass" | "order-book"
  | "limit-up" | "broken-limit" | "limit-down" | "seal-rate" | "risk-stocks"
  | "sector-total" | "sector-positive" | "sector-limit" | "top-sector" | "top-sector-breadth" | "top-sector-amount"
  | "sentiment" | "rising" | "falling" | "market-amount" | "regime" | "risk-score" | "heat-score"
  | "active-stocks" | "top-stock" | "high-amplitude" | "attention-top" | "theme-stock-top"
  | "history-coverage" | "history-new-high" | "history-previous-limit" | "interval-result"
  | "consecutive-count" | "top-board" | "first-board" | "volume-breakout" | "previous-high" | "low-volume"
  | "seat-stocks" | "seat-count" | "seat-net" | "top-seat"
  | "large-order" | "large-order-buy" | "large-order-sell" | "large-order-net"
  | "sector-flow" | "sector-flow-timeline" | "sector-flow-direction" | "sector-flow-persistence" | "iwencai"
  | "review-date" | "review-quality";

export const WORKSPACE_INSIGHT_PROFILES: Record<string, readonly MetricKey[]> = {
  "盘中异动": ["anomaly-total", "anomaly-positive", "anomaly-symbols", "top-theme"],
  "异动语音播报": ["anomaly-negative", "anomaly-total", "latest-news", "anomaly-symbols"],
  "AI+题材": ["theme-confluence", "news-verified", "theme-symbols", "top-theme"],
  "隔夜单/抢筹": ["gap-up", "gap-recovery", "auction-pass", "order-book"],
  "竞价封单": ["limit-up", "gap-up", "seal-rate", "order-book"],
  "板块精选": ["top-sector", "top-sector-breadth", "sector-limit", "top-sector-amount"],
  "涨停板": ["limit-up", "broken-limit", "seal-rate", "sector-limit"],
  "连板表现": ["consecutive-count", "top-board", "history-coverage", "review-date"],
  "龙头晋级": ["limit-up", "sector-limit", "theme-stock-top", "history-coverage"],
  "竞价异动": ["gap-up", "gap-down", "gap-recovery", "high-amplitude"],
  "竞价选股": ["auction-pass", "gap-up", "risk-stocks", "order-book"],
  "板块赛道": ["sector-positive", "top-sector", "top-sector-amount", "sector-total"],
  "板块涨停": ["sector-limit", "limit-up", "top-sector-breadth", "seal-rate"],
  "炸板": ["broken-limit", "seal-rate", "risk-stocks", "limit-down"],
  "题材库": ["theme-total", "news-total", "theme-symbols", "latest-news"],
  "情绪周期": ["sentiment", "regime", "risk-score", "heat-score"],
  "游资追踪": ["seat-count", "seat-stocks", "top-seat", "review-date"],
  "游资动向": ["seat-net", "seat-count", "seat-stocks", "top-seat"],
  "人气榜": ["attention-top", "news-symbols", "theme-stock-top", "active-stocks"],
  "七大人气榜": ["top-stock", "attention-top", "high-amplitude", "theme-stock-top"],
  "百日新高": ["history-new-high", "history-coverage", "review-date", "review-quality"],
  "百日新高趋势": ["history-new-high", "interval-result", "history-coverage", "risk-stocks"],
  "区间统计": ["interval-result", "history-coverage", "review-date", "active-stocks"],
  "热点播报": ["latest-news", "news-total", "news-symbols", "top-theme"],
  "题材挖掘": ["theme-confluence", "theme-total", "news-verified", "theme-symbols"],
  "概念叠加": ["theme-stock-top", "theme-confluence", "theme-total", "risk-stocks"],
  "龙头梯队": ["limit-up", "top-stock", "sector-limit", "risk-stocks"],
  "涨停复盘啦": ["limit-up", "broken-limit", "limit-down", "review-date"],
  "复盘统计大全": ["rising", "falling", "market-amount", "review-quality"],
  "异动统计大全": ["anomaly-total", "anomaly-positive", "anomaly-negative", "theme-total"],
  "AI+选股": ["auction-pass", "regime", "theme-confluence", "risk-stocks"],
  "投资日历": ["latest-news", "news-total", "news-verified", "review-date"],
  "强度风口": ["top-sector", "sector-limit", "top-sector-breadth", "theme-confluence"],
  "昨涨停": ["history-previous-limit", "history-coverage", "review-date", "risk-stocks"],
  "跌停板": ["limit-down", "risk-stocks", "falling", "broken-limit"],
  "个股详情": ["top-stock", "high-amplitude", "theme-stock-top", "latest-news"],
  "主力大单监控": ["large-order", "large-order-buy", "large-order-sell", "large-order-net"],
  "问财选股": ["iwencai", "auction-pass", "regime", "history-coverage"],
  "异动提醒": ["anomaly-negative", "anomaly-positive", "anomaly-symbols", "latest-news"],
  "板块资金动图": ["sector-flow", "sector-flow-timeline", "sector-flow-direction", "sector-flow-persistence"],
  "个股异动": ["high-amplitude", "gap-up", "gap-down", "anomaly-symbols"],
  "开盘啦": ["sentiment", "gap-up", "gap-down", "top-theme"],
  "热点解读": ["news-verified", "top-theme", "theme-symbols", "attention-top"],
  "非研产业库": ["theme-total", "theme-symbols", "news-verified", "sector-total"],
  "连板梯队": ["top-board", "consecutive-count", "history-coverage", "review-quality"],
  "首板梯队": ["first-board", "history-coverage", "market-amount", "review-date"],
  "放量突破": ["volume-breakout", "history-coverage", "market-amount", "review-quality"],
  "突破前高": ["previous-high", "history-coverage", "top-stock", "review-date"],
  "低位放量": ["low-volume", "history-coverage", "risk-stocks", "review-date"],
  "龙虎榜": ["seat-stocks", "seat-net", "seat-count", "review-date"],
};

const ready = (
  key: MetricKey,
  label: string,
  value: string,
  detail: string,
  tone: InsightTone,
  icon: WorkspaceInsight["icon"],
  basis: Exclude<InsightBasis, "unavailable"> = "raw",
  method?: string,
): WorkspaceInsight => ({ key, label, value, detail, quality: "ready", tone, basis, method, icon });
const unavailable = (key: MetricKey, label: string, detail: string, icon: WorkspaceInsight["icon"]): WorkspaceInsight => ({ key, label, value: "未接入", detail, quality: "unavailable", tone: "warning", basis: "unavailable", icon });
const countSymbols = (items: Array<{ symbols: string[] }>) => new Set(items.flatMap((item) => item.symbols)).size;
const signedMoney = (value: number) => `${value >= 0 ? "+" : ""}${value.toFixed(2)}亿`;
const known = (value: number | null | undefined): value is number => value !== null && value !== undefined && Number.isFinite(value);
const compareDesc = (a: number | null, b: number | null): number => {
  if (!known(a) && !known(b)) return 0;
  if (!known(a)) return 1;
  if (!known(b)) return -1;
  return b - a;
};

const MARKET_DEPENDENT_METRICS: Partial<Record<MetricKey, string>> = {
  "gap-up": "高开样本", "gap-down": "低开样本", "gap-recovery": "高开延续",
  "auction-pass": "竞价规则通过", "limit-up": "严格涨停", "broken-limit": "触板未封",
  "limit-down": "当前跌停", "seal-rate": "封板率", "risk-stocks": "风险股票",
  "sector-total": "板块样本", "sector-positive": "上涨板块", "sector-limit": "涨停扩散板块",
  "top-sector": "综合强度第一", "top-sector-breadth": "领涨板块广度", "top-sector-amount": "板块成交活跃",
  "sentiment": "市场情绪", "rising": "上涨家数", "falling": "下跌家数", "market-amount": "两市成交",
  "regime": "市场风格", "risk-score": "市场风险分", "heat-score": "市场热度分",
  "active-stocks": "行情样本", "top-stock": "涨幅领先", "high-amplitude": "最大振幅",
  "attention-top": "观察热度第一", "theme-stock-top": "题材叠加最多",
};

function metric(key: MetricKey, data: MarketOverviewResponse, model: WorkspaceMarketModel): WorkspaceInsight {
  const review = data.review;
  const hasVerifiedHistory = Boolean(
    review
    && review.history_ready_count > 0
    && review.source !== "unavailable"
    && review.quality !== "unavailable",
  );
  const seatEvidenceReady = hasDragonTigerEvidence(review);
  const seats = review?.dragon_tiger.flatMap((item) => item.seats) ?? [];
  const seatNetValues = seats.map((item) => numberValue(item.net_amount_yi)).filter((value): value is number => value !== null);
  const seatNet = seatNetValues.length ? seatNetValues.reduce((sum, value) => sum + value, 0) : null;
  const topSeat = [...seats].filter((item) => numberValue(item.net_amount_yi) !== null).sort((a, b) => Math.abs(numberValue(b.net_amount_yi) as number) - Math.abs(numberValue(a.net_amount_yi) as number))[0];
  const topSector = model.sectors[0];
  const topStock = [...model.stocks].filter((item) => known(item.change)).sort((a, b) => compareDesc(a.change, b.change))[0];
  const topAttention = [...model.stocks].filter((item) => known(item.attentionScore)).sort((a, b) => compareDesc(a.attentionScore, b.attentionScore))[0];
  const topThemeStock = [...model.stocks].filter((item) => item.themes.length > 0).sort((a, b) => b.themes.length - a.themes.length)[0];
  const topAmplitude = [...model.stocks].filter((item) => known(item.amplitude)).sort((a, b) => compareDesc(a.amplitude, b.amplitude))[0];
  const gapsUp = model.stocks.filter((item) => known(item.gap) && item.gap >= 2);
  const gapsDown = model.stocks.filter((item) => known(item.gap) && item.gap <= -2);
  const auctionPass = model.stocks.filter((item) => known(item.gap) && known(item.change) && known(item.closePosition) && known(item.amount) && item.gap >= -1 && item.gap <= 4 && item.change >= item.gap - 1 && item.closePosition >= 50 && item.amount > 0);
  const riskStocks = model.stocks.filter((item) => item.state === "broken_limit_up" || item.state === "limit_down" || (known(item.change) && item.change <= -3));
  const coverage = review && review.universe_count > 0 ? review.history_ready_count / review.universe_count * 100 : null;
  const sectorFlowPoints = data.sector_fund_flow ?? [];
  const latestSectorFlowByCode = new Map<string, typeof sectorFlowPoints[number]>();
  const sectorFlowCounts = new Map<string, number>();
  for (const point of sectorFlowPoints) {
    sectorFlowCounts.set(point.sector_code, (sectorFlowCounts.get(point.sector_code) ?? 0) + 1);
    const previous = latestSectorFlowByCode.get(point.sector_code);
    if (!previous || point.observed_at > previous.observed_at) latestSectorFlowByCode.set(point.sector_code, point);
  }
  const latestSectorFlow = [...latestSectorFlowByCode.values()];
  const sectorFlowNet = latestSectorFlow.reduce((sum, point) => sum + Number(point.main_net_yi), 0);
  const sectorFlowLeader = [...latestSectorFlow]
    .filter((point) => Number.isFinite(Number(point.main_net_yi)))
    .sort((left, right) => Number(right.main_net_yi) - Number(left.main_net_yi))[0];
  const sectorFlowPersistent = [...sectorFlowCounts.values()].filter((count) => count >= 2).length;
  const sectorFlowQuality = latestSectorFlow.length > 0 && latestSectorFlow.every((point) => point.quality === "ready") ? "positive" : "warning";
  const largeOrderFlows = (data.large_order_flows ?? []).filter((item) => Number.isFinite(Number(item.main_net_yi)));
  const largeOrderNet = largeOrderFlows.reduce((sum, item) => sum + Number(item.main_net_yi), 0);
  const largeOrderInflowCount = largeOrderFlows.filter((item) => Number(item.main_net_yi) > 0).length;
  const largeOrderOutflowCount = largeOrderFlows.filter((item) => Number(item.main_net_yi) < 0).length;
  const largeOrderDetail = `${largeOrderFlows.length} 只真实资金流样本 · ${largeOrderInflowCount} 只流入 / ${largeOrderOutflowCount} 只流出`;
  const withLargeOrderFreshness = (insight: WorkspaceInsight): WorkspaceInsight => (
    largeOrderFlows.every((item) => item.quality === "ready")
      ? insight
      : { ...insight, quality: "partial", tone: "warning", detail: `${insight.detail} · 部分缓存待刷新` }
  );

  if ((data.status === "unavailable" || data.market_data.quality === "unavailable") && MARKET_DEPENDENT_METRICS[key]) {
    return unavailable(key, MARKET_DEPENDENT_METRICS[key], "行情主源不可用，暂不计算该指标", "data");
  }

  switch (key) {
    case "anomaly-total": return ready(key, "已验证异动", String(model.anomalies.length), "本地异动库记录", "neutral", "pulse");
    case "anomaly-positive": return ready(key, "正向异动", String(model.anomalies.filter((item) => item.direction === "positive").length), "按事件方向统计", "positive", "pulse");
    case "anomaly-negative": return ready(key, "风险异动", String(model.anomalies.filter((item) => item.direction === "negative").length), "优先核验风险事件", "danger", "risk");
    case "anomaly-symbols": return ready(key, "影响股票", String(countSymbols(model.anomalies)), "异动已关联代码去重", "neutral", "stock");
    case "news-total": return ready(key, "A 股资讯", String(model.news.length), "仅统计已关联 A 股", "neutral", "news");
    case "news-verified": return ready(key, "已核验资讯", String(model.news.filter((item) => item.review_state === "verified").length), "按本地复核状态", "positive", "news");
    case "news-symbols": return ready(key, "资讯关联股票", String(countSymbols(model.news)), "新闻代码去重", "neutral", "stock");
    case "latest-news": return ready(key, "最新入库", model.news[0]?.occurred_at.slice(11, 16) ?? "--", model.news[0]?.headline ?? "当前无 A 股关联资讯", "neutral", "news");
    case "theme-total": return ready(key, "可追溯题材", String(model.themes.length), "来自新闻与异动标签", "neutral", "theme");
    case "top-theme": return ready(key, "证据最多题材", model.themes[0]?.name ?? "--", model.themes[0] ? `${model.themes[0].evidenceCount} 条证据` : "暂无题材证据", "positive", "theme");
    case "theme-symbols": return ready(key, "题材关联股票", String(new Set(model.themes.flatMap((item) => item.symbols)).size), "题材代码去重", "neutral", "stock");
    case "theme-confluence": return ready(key, "多源共振题材", String(model.themes.filter((item) => item.newsCount > 0 && item.anomalyCount > 0).length), "新闻与异动同时出现", "positive", "theme");
    case "gap-up": return ready(key, "高开 >= 2%", String(gapsUp.length), "开盘价相对昨收", "positive", "auction", "derived", "(开盘价 / 昨收 - 1) × 100");
    case "gap-down": return ready(key, "低开 <= -2%", String(gapsDown.length), "开盘价相对昨收", "danger", "auction", "derived", "(开盘价 / 昨收 - 1) × 100");
    case "gap-recovery": return ready(key, "高开延续", String(gapsUp.filter((item) => known(item.change) && item.change >= (item.gap ?? 0) - 1).length), "现涨幅未明显弱于缺口", "positive", "auction", "derived", "现涨幅 >= 高开幅度 - 1 个百分点");
    case "auction-pass": return ready(key, "竞价规则通过", String(auctionPass.length), "缺口、现价、收盘位置、成交均通过", "positive", "auction", "derived", "-1%≤高开≤4%、现涨幅≥高开-1%、收盘位置≥50%、成交额>0");
    case "order-book": return unavailable(key, "委托/封单证据", "当前响应没有逐笔委托队列", "data");
    case "limit-up": return ready(key, "严格涨停", String(data.limit_ecology.limit_up_count), "按现价与涨停价判定", "positive", "limit");
    case "broken-limit": return ready(key, "触板未封", String(data.limit_ecology.broken_limit_up_count), "最高触板但现价未封", "warning", "risk");
    case "limit-down": return ready(key, "当前跌停", String(data.limit_ecology.limit_down_count), "严格现价风险状态", "danger", "risk");
    case "seal-rate": return ready(key, "封板率", data.limit_ecology.seal_rate_percent ? `${data.limit_ecology.seal_rate_percent}%` : "--", "封板 / 全部触板", "positive", "limit");
    case "risk-stocks": return ready(key, "风险股票", String(riskStocks.length), "跌停、炸板或跌幅 <= -3%", "danger", "risk", "derived", "状态为跌停/炸板，或现涨幅≤-3%");
    case "sector-total": return ready(key, "板块样本", String(model.sectors.length), "本地板块快照", "neutral", "sector");
    case "sector-positive": return ready(key, "上涨板块", String(model.sectors.filter((item) => known(item.change) && item.change > 0).length), "板块涨跌幅 > 0", "positive", "sector");
    case "sector-limit": return ready(key, "涨停扩散板块", String(model.sectors.filter((item) => item.limit_up_count > 0).length), "板块内至少 1 只涨停", "positive", "sector");
    case "top-sector": return topSector && known(topSector.strengthScore) ? ready(key, "综合强度第一", topSector.name, `强度 ${topSector.strengthScore.toFixed(0)} / 100`, "positive", "sector", "composite", "30 + 6×涨跌幅 + 0.45×(上涨广度-50) + min(20, 4×涨停密度)，截断 0-100") : unavailable(key, "综合强度第一", "板块强度所需字段不足", "sector");
    case "top-sector-breadth": return topSector && known(topSector.breadthPercent) ? ready(key, "领涨板块广度", `${topSector.breadthPercent.toFixed(0)}%`, topSector.name, "positive", "sector", "derived", "上涨家数 / (上涨家数 + 下跌家数)") : unavailable(key, "领涨板块广度", "板块上涨/下跌家数不足", "sector");
    case "top-sector-amount": return topSector && known(topSector.amount) ? ready(key, "板块成交活跃", `${topSector.amount.toFixed(0)}亿`, "仅表示成交额，不代表净流入", "neutral", "sector", "raw", "板块成交额字段；不等同于资金净流入") : unavailable(key, "板块成交活跃", "板块成交额不可用", "sector");
    case "sentiment": return numberValue(data.sentiment.score) !== null
      ? ready(key, "市场情绪", data.sentiment.score as string, data.sentiment.band, "neutral", "pulse", "composite", "a-share-sentiment-v2：9 因子按 15/15/10/10/15/15/10/5/5 加权，按有效覆盖归一化")
      : unavailable(key, "市场情绪", "情绪分数缺失，不能生成市场情绪结论", "pulse");
    case "rising": return data.breadth.valid_count > 0
      ? ready(key, "上涨家数", String(data.breadth.rising_count), `${data.breadth.valid_count} 只有效行情`, "positive", "pulse")
      : unavailable(key, "上涨家数", "有效行情样本为 0，暂不统计", "pulse");
    case "falling": return data.breadth.valid_count > 0
      ? ready(key, "下跌家数", String(data.breadth.falling_count), `${data.breadth.valid_count} 只有效行情`, "danger", "pulse")
      : unavailable(key, "下跌家数", "有效行情样本为 0，暂不统计", "pulse");
    case "market-amount": return numberValue(data.liquidity.total_amount_yi) !== null
      ? ready(key, "两市成交", `${data.liquidity.total_amount_yi}亿`, data.liquidity.relative_amount ? `基准 ${data.liquidity.relative_amount}x` : "历史基准不足", "neutral", "pulse")
      : unavailable(key, "两市成交", "全市场成交额字段不可用", "pulse");
    case "regime": return data.regime?.regime
      ? ready(key, "市场风格", data.regime.regime, `仓位系数 ${data.regime.market_coef}`, "neutral", "pulse")
      : unavailable(key, "市场风格", "风格判定缺少有效因子或规则未匹配", "pulse");
    case "risk-score": return numberValue(data.regime?.risk_score) !== null
      ? ready(key, "市场风险分", data.regime?.risk_score as string, data.regime?.quality === "ready" ? "风格模型已核验" : "因子部分可用", "danger", "risk")
      : unavailable(key, "市场风险分", "风险因子不足，暂不计算", "risk");
    case "heat-score": return numberValue(data.regime?.heat_score) !== null
      ? ready(key, "市场热度分", data.regime?.heat_score as string, data.regime?.quality === "ready" ? "风格模型已核验" : "因子部分可用", "positive", "pulse")
      : unavailable(key, "市场热度分", "热度因子不足，暂不计算", "pulse");
    case "active-stocks": return ready(key, "行情样本", String(model.stocks.length), "接口返回的代表股票", "neutral", "stock");
    case "top-stock": return topStock && known(topStock.change) ? ready(key, "涨幅领先", topStock.name, `${topStock.symbol} ${topStock.change >= 0 ? "+" : ""}${topStock.change.toFixed(2)}%`, "positive", "stock") : unavailable(key, "涨幅领先", "行情样本缺少涨跌幅", "stock");
    case "high-amplitude": return topAmplitude && known(topAmplitude.amplitude) ? ready(key, "最大振幅", `${topAmplitude.amplitude.toFixed(2)}%`, `${topAmplitude.name} ${topAmplitude.symbol}`, "warning", "stock") : unavailable(key, "最大振幅", "行情样本缺少高低价", "stock");
    case "attention-top": return topAttention && known(topAttention.attentionScore) ? ready(key, "观察热度第一", topAttention.name, `量价资讯合成分 ${topAttention.attentionScore.toFixed(0)}`, "positive", "stock", "composite", "35 + 2×|涨跌幅| + min(20, 10×log10(成交额亿+1)) + 5×题材数，截断 0-100"): unavailable(key, "观察热度第一", "行情与关联证据不足", "stock");
    case "theme-stock-top": return topThemeStock
      ? ready(key, "题材叠加最多", topThemeStock.name, `${topThemeStock.themes.length} 个已关联题材`, "warning", "theme")
      : unavailable(key, "题材叠加最多", "没有股票同时具备已关联题材证据", "theme");
    case "history-coverage": return hasVerifiedHistory && review && review.universe_count > 0 && coverage !== null
      ? ready(key, "日线覆盖", `${coverage.toFixed(1)}%`, `${review.history_ready_count}/${review.universe_count}`, coverage >= 80 ? "positive" : "warning", "history", "derived", "可用日线股票数 / 全市场股票数")
      : unavailable(key, "日线覆盖", "本地日线没有可用历史样本", "history");
    case "history-new-high": return hasVerifiedHistory && review && Array.isArray(review.new_high_100)
      ? ready(key, "百日新高清单", String(review.new_high_100.length), `${review.latest_trade_date ?? "复盘交易日待确认"} · 完整日线筛选`, "positive", "history")
      : unavailable(key, "百日新高清单", "本地日线没有可验证的百日窗口", "history");
    case "history-previous-limit": return hasVerifiedHistory && review && Array.isArray(review.previous_limit_up)
      ? ready(key, "昨涨停反馈", String(review.previous_limit_up.length), `${review.latest_trade_date ?? "复盘交易日待确认"} · 上一交易日严格涨停`, "neutral", "history")
      : unavailable(key, "昨涨停反馈", "本地日线没有可验证的上一交易日名单", "history");
    case "interval-result": return unavailable(key, "区间统计结果", "尚未选择并计算明确起止区间", "history");
    case "consecutive-count": return review ? ready(key, "连续涨停", String(review.consecutive_limit_up.length), "至少 2 个交易日连续收盘涨停", "positive", "history") : unavailable(key, "连续涨停", "本地日线复盘尚未完成", "history");
    case "top-board": {
      const boardHeights = review?.consecutive_limit_up.map((item) => item.board_count).filter((value): value is number => known(value)) ?? [];
      return boardHeights.length ? ready(key, "最高连板", `${Math.max(...boardHeights)}板`, "来自本地连续日线", "positive", "history") : unavailable(key, "最高连板", "本地连续日线没有可用连板高度", "history");
    }
    case "first-board": return review ? ready(key, "首板股票", String(review.first_limit_up.length), "当日涨停且上一日未涨停", "positive", "history") : unavailable(key, "首板股票", "本地日线复盘尚未完成", "history");
    case "volume-breakout": return review ? ready(key, "放量突破", String(review.volume_breakouts.length), "60 日收盘新高且量能 >= 1.8x", "positive", "history") : unavailable(key, "放量突破", "本地日线复盘尚未完成", "history");
    case "previous-high": return review ? ready(key, "突破前高", String(review.previous_high_breakouts.length), "突破前 20 日高点并放量", "positive", "history") : unavailable(key, "突破前高", "本地日线复盘尚未完成", "history");
    case "low-volume": return review ? ready(key, "低位放量", String(review.low_position_volume.length), "120 日区间下部且放量", "warning", "history") : unavailable(key, "低位放量", "本地日线复盘尚未完成", "history");
    case "seat-stocks": return seatEvidenceReady ? ready(key, "上榜股票", String(review!.dragon_tiger.length), "东方财富公开龙虎榜", "neutral", "seat") : unavailable(key, "上榜股票", "龙虎榜接口和本地缓存均不可用", "seat");
    case "seat-count": return seatEvidenceReady ? ready(key, "可验证席位", String(seats.length), "含席位名称及买卖金额", "neutral", "seat") : unavailable(key, "可验证席位", "龙虎榜席位尚未取得", "seat");
    case "seat-net": return seatEvidenceReady && seatNet !== null ? ready(key, "席位净买额", signedMoney(seatNet), "按公开席位净额合计", seatNet >= 0 ? "positive" : "danger", "seat") : unavailable(key, "席位净买额", "龙虎榜席位净额字段不足", "seat");
    case "top-seat": return seatEvidenceReady && topSeat ? ready(key, "净额最大席位", topSeat.seat_name, signedMoney(numberValue(topSeat.net_amount_yi) as number), "neutral", "seat") : unavailable(key, "净额最大席位", "龙虎榜席位净额字段不足", "seat");
    case "large-order": return largeOrderFlows.length
      ? withLargeOrderFreshness(ready(
        key,
        "样本主力方向",
        largeOrderNet > 0 ? "净流入" : largeOrderNet < 0 ? "净流出" : "均衡",
        largeOrderDetail,
        largeOrderNet > 0 ? "positive" : largeOrderNet < 0 ? "danger" : "neutral",
        "data",
        "derived",
        "按真实个股主力净额合计判定方向；主力净额为大单与超大单净额之和",
      ))
      : unavailable(key, "样本主力方向", "尚未取得真实个股资金流样本，后台将按高成交活跃股票分批补齐", "data");
    case "large-order-buy": return unavailable(key, "大单买入额", "东财资金流仅提供大单净额，未提供可核验的买入总额", "data");
    case "large-order-sell": return unavailable(key, "大单卖出额", "东财资金流仅提供大单净额，未提供可核验的卖出总额", "data");
    case "large-order-net": return largeOrderFlows.length
      ? withLargeOrderFreshness(ready(
        key,
        "大单净流入",
        signedMoney(largeOrderNet),
        `${largeOrderFlows.length} 只真实样本主力净额合计`,
        largeOrderNet > 0 ? "positive" : largeOrderNet < 0 ? "danger" : "neutral",
        "data",
        "derived",
        "样本内各股主力净额求和；主力净额为大单与超大单净额之和",
      ))
      : unavailable(key, "大单净流入", "尚未取得真实个股大单与超大单净额", "data");
    case "sector-flow": return latestSectorFlow.length
      ? ready(key, "板块净流入合计", signedMoney(sectorFlowNet), `${latestSectorFlow.length} 个板块最新主力净流入`, sectorFlowNet >= 0 ? "positive" : "danger", "sector", "raw", "最新各板块主力净流入求和")
      : unavailable(key, "板块净流入合计", "没有取得真实板块主力净流入快照", "data");
    case "sector-flow-timeline": return sectorFlowPoints.length
      ? ready(key, "资金时间序列", `${new Set(sectorFlowPoints.map((point) => point.observed_at)).size}次`, `${latestSectorFlow.length} 个板块 · 每个点保留自身新鲜度`, sectorFlowQuality, "sector", "raw", "按观测时间去重的真实采样次数")
      : unavailable(key, "资金时间序列", "未取得逐时板块净流入记录", "data");
    case "sector-flow-direction": return sectorFlowLeader
      ? ready(key, "净流入领先板块", sectorFlowLeader.sector_name, signedMoney(Number(sectorFlowLeader.main_net_yi)), Number(sectorFlowLeader.main_net_yi) >= 0 ? "positive" : "danger", "sector", "raw", "按最新主力净流入排序")
      : unavailable(key, "净流入领先板块", "没有可排序的板块净流入字段", "data");
    case "sector-flow-persistence": return sectorFlowPoints.length
      ? ready(key, "连续采样板块", `${sectorFlowPersistent}个`, "至少出现 2 次真实采样的板块数量", sectorFlowPersistent > 0 ? "positive" : "warning", "sector", "derived", "按板块代码统计采样次数 >= 2")
      : unavailable(key, "连续采样板块", "没有连续净流入序列，不能测算持续性", "data");
    case "iwencai": return unavailable(key, "问财语义结果", "当前执行的是本地规则，不冒充问财官方结果", "data");
    case "review-date": return review?.latest_trade_date
      ? ready(key, "复盘交易日", review.latest_trade_date, "本地日线复盘日期", "neutral", "history")
      : unavailable(key, "复盘交易日", "本地日线复盘尚未完成", "history");
    case "review-quality": return review
      ? ready(key, "复盘质量", review.quality === "ready" ? "完整" : review.quality === "partial" ? "部分" : "待准备", review.source ?? "暂无复盘来源", review.quality === "ready" ? "positive" : "warning", "data")
      : unavailable(key, "复盘质量", "本地日线复盘尚未完成", "data");
  }
}

export function buildWorkspaceInsights(feature: string, data: MarketOverviewResponse, model: WorkspaceMarketModel): WorkspaceInsight[] {
  const profile = WORKSPACE_INSIGHT_PROFILES[feature];
  if (!profile) throw new Error(`信息总览缺少关键指标定义：${feature}`);
  return profile.map((key) => {
    const rawInsight = metric(key, data, model);
    const staleReview = Boolean(
      REVIEW_KEYS.has(key)
      && data.review
      && (data.review.refresh_required || data.review.quality === "partial" || data.review.quality === "stale"),
    );
    const insight = staleReview
      ? {
        ...rawInsight,
        quality: rawInsight.quality === "unavailable" ? "unavailable" as const : "partial" as const,
        tone: rawInsight.quality === "unavailable" ? rawInsight.tone : "warning" as const,
        detail: `${rawInsight.detail} · 实际复盘日 ${data.review?.latest_trade_date ?? "未知"} · 数据待补齐：${data.review?.refresh_reason ?? "历史数据待补齐"}`,
      }
      : rawInsight;
    const drilldown = insightDrilldown(key, insight, data, model);
    const contract = workspaceMetricContract(key, insight, drilldown, data);
    return { ...insight, contract, drilldown: { ...drilldown, contract } };
  });
}

const REVIEW_KEYS = new Set<MetricKey>([
  "history-coverage", "history-new-high", "history-previous-limit", "interval-result",
  "consecutive-count", "top-board", "first-board", "volume-breakout", "previous-high",
  "low-volume", "seat-stocks", "seat-count", "seat-net", "top-seat", "review-date", "review-quality",
]);

const COUNT_KEYS = new Set<MetricKey>([
  "anomaly-total", "anomaly-positive", "anomaly-negative", "anomaly-symbols", "news-total",
  "news-verified", "news-symbols", "theme-total", "theme-symbols", "gap-up", "gap-down",
  "gap-recovery", "auction-pass", "limit-up", "broken-limit", "limit-down", "risk-stocks",
  "sector-total", "sector-positive", "sector-limit", "rising", "falling", "active-stocks",
  "history-new-high", "history-previous-limit", "consecutive-count", "first-board", "volume-breakout",
  "previous-high", "low-volume", "seat-stocks", "seat-count", "large-order", "large-order-buy", "large-order-sell",
]);

function integerValue(value: string): number | null {
  const match = value.replaceAll(",", "").match(/^-?\d+$/);
  return match ? Number(match[0]) : null;
}

function workspaceMetricContract(
  key: MetricKey,
  insight: WorkspaceInsight,
  drilldown: MetricDrilldownSelection,
  data: MarketOverviewResponse,
): MetricContract {
  const reviewMetric = REVIEW_KEYS.has(key);
  const sectorFlowMetric = key.startsWith("sector-flow");
  const largeOrderMetric = key.startsWith("large-order");
  const members = drilldown.stocks ?? [];
  const parsedTotal = COUNT_KEYS.has(key) ? integerValue(insight.value) : null;
  const totalCount = parsedTotal !== null && parsedTotal >= members.length ? parsedTotal : null;
  const latestSectorFlowPoint = sectorFlowMetric
    ? [...(data.sector_fund_flow ?? [])].sort((left, right) => right.observed_at.localeCompare(left.observed_at))[0]
    : undefined;
  const latestLargeOrderPoint = largeOrderMetric
    ? [...(data.large_order_flows ?? [])].sort((left, right) => right.observed_at.localeCompare(left.observed_at))[0]
    : undefined;
  const observedAt = reviewMetric
    ? data.review?.observed_at ?? data.market_data.observed_at ?? data.observed_at ?? data.sentiment.observed_at
    : latestLargeOrderPoint?.observed_at ?? latestSectorFlowPoint?.observed_at ?? data.market_data.observed_at ?? data.observed_at ?? data.sentiment.observed_at;
  const tradeDate = reviewMetric
    ? data.review?.latest_trade_date ?? data.as_of ?? observedAt?.slice(0, 10)
    : data.as_of ?? observedAt?.slice(0, 10);
  const source = reviewMetric
    ? data.review?.source ?? "本地日线复盘未接入"
    : latestLargeOrderPoint?.source ?? latestSectorFlowPoint?.source ?? (data.market_data.source || data.sources?.join(" / ") || "数据源未提供");
  const sampleCount = reviewMetric
    ? data.review?.history_ready_count ?? null
    : largeOrderMetric
      ? data.large_order_flows?.length ?? null
      : data.market_data.quote_count || data.breadth.valid_count || null;
  const unavailableReason = drilldown.unavailableReason
    ?? (insight.quality === "unavailable" ? insight.detail : null);
  return createMetricContract({
    metricId: `market-overview.${key}`,
    label: insight.label,
    value: insight.value,
    scope: insight.method ?? insight.detail,
    status: insight.quality,
    tradeDate,
    observedAt: observedAt || null,
    source,
    formulaVersion: reviewMetric ? data.review?.formula_version ?? null : insight.method ? "workspace-insight-v1" : null,
    sampleCount,
    totalCount,
    drilldownKind: drilldown.stocks ? "members" : "aggregate_only",
    members: members.map((member) => ({
      symbol: member.symbol,
      name: member.name,
      reason: member.reason,
      value: typeof member.value === "string" || typeof member.value === "number" ? member.value : null,
    })),
    unavailableReason,
  });
}

function insightDrilldown(key: MetricKey, insight: WorkspaceInsight, data: MarketOverviewResponse, model: WorkspaceMarketModel): MetricDrilldownSelection {
  const stock = (item: WorkspaceMarketModel["stocks"][number], reason: string) => ({
    symbol: item.symbol, name: item.name?.trim() || "名称待补齐", reason,
    value: known(item.change) ? `${item.change > 0 ? "+" : ""}${item.change.toFixed(2)}%` : "--",
  });
  const reviewStock = (item: NonNullable<MarketOverviewResponse["review"]>["first_limit_up"][number], reason: string) => ({
    symbol: item.symbol, name: item.name?.trim() || "名称待补齐", reason,
    value: numberValue(item.change_percent) === null ? "--" : `${Number(item.change_percent) > 0 ? "+" : ""}${Number(item.change_percent).toFixed(2)}%`,
  });
  const listedStock = (item: NonNullable<MarketOverviewResponse["review"]>["dragon_tiger"][number], reason: string) => ({
    symbol: item.symbol, name: item.name?.trim() || "名称待补齐", reason,
    value: numberValue(item.change_percent) === null ? "--" : `${Number(item.change_percent) > 0 ? "+" : ""}${Number(item.change_percent).toFixed(2)}%`,
  });
  const aggregate = (reason: string): MetricDrilldownSelection => ({ label: insight.label, value: insight.value, source: insight.detail, unavailableReason: reason });
  const exact = (stocks: MetricDrilldownSelection["stocks"], totalLabel?: string): MetricDrilldownSelection => ({ label: insight.label, value: insight.value, source: insight.detail, stocks, totalLabel });
  const linkedSymbols = (items: Array<{ symbols: string[]; headline?: string; label?: string }>, prefix: string) => {
    const reasons = new Map<string, string[]>();
    items.forEach((item) => item.symbols.forEach((symbol) => reasons.set(symbol, [...(reasons.get(symbol) ?? []), item.headline ?? item.label ?? prefix])));
    return [...reasons.entries()].map(([symbol, values]) => ({ symbol, name: model.stockNames.get(symbol) ?? "名称待补齐", reason: `${prefix}：${[...new Set(values)].join(" / ")}` }));
  };
  const gapsUp = model.stocks.filter((item) => known(item.gap) && item.gap >= 2);
  const gapsDown = model.stocks.filter((item) => known(item.gap) && item.gap <= -2);
  const riskStocks = model.stocks.filter((item) => item.state === "broken_limit_up" || item.state === "limit_down" || (known(item.change) && item.change <= -3));

  switch (key) {
    case "anomaly-total": return exact(linkedSymbols(model.anomalies, "异动事件"), "事件统计");
    case "anomaly-positive": return exact(linkedSymbols(model.anomalies.filter((item) => item.direction === "positive"), "正向异动"), "事件统计");
    case "anomaly-negative": return exact(linkedSymbols(model.anomalies.filter((item) => item.direction === "negative"), "风险异动"), "事件统计");
    case "anomaly-symbols": return exact(linkedSymbols(model.anomalies, "异动关联"));
    case "news-total": return exact(linkedSymbols(model.news, "资讯关联"), "资讯统计");
    case "news-verified": return exact(linkedSymbols(model.news.filter((item) => item.review_state === "verified"), "已核验资讯"), "资讯统计");
    case "news-symbols": return exact(linkedSymbols(model.news, "资讯关联"));
    case "theme-symbols": return exact([...new Set(model.themes.flatMap((item) => item.symbols))].map((symbol) => ({ symbol, name: model.stockNames.get(symbol) ?? "名称待补齐", reason: `已关联题材：${model.themes.filter((item) => item.symbols.includes(symbol)).map((item) => item.name).join(" / ")}` })));
    case "gap-up": return exact(gapsUp.map((item) => stock(item, `高开 ${item.gap!.toFixed(2)}%`)));
    case "gap-down": return exact(gapsDown.map((item) => stock(item, `低开 ${item.gap!.toFixed(2)}%`)));
    case "gap-recovery": return exact(gapsUp.filter((item) => known(item.change) && item.change >= item.gap! - 1).map((item) => stock(item, `高开 ${item.gap!.toFixed(2)}%，当前涨幅保持`)));
    case "auction-pass": return exact(model.stocks.filter((item) => known(item.gap) && known(item.change) && known(item.closePosition) && known(item.amount) && item.gap >= -1 && item.gap <= 4 && item.change >= item.gap - 1 && item.closePosition >= 50 && item.amount > 0).map((item) => stock(item, "缺口、现价、收盘位置和成交额均通过")));
    case "limit-up": return exact(model.stocks.filter((item) => item.state === "limit_up").map((item) => stock(item, "当前价格达到严格涨停状态")), "全市场统计");
    case "broken-limit": return exact(model.stocks.filter((item) => item.state === "broken_limit_up").map((item) => stock(item, "最高触板但当前未封住涨停")), "全市场统计");
    case "limit-down": return exact(model.stocks.filter((item) => item.state === "limit_down").map((item) => stock(item, "当前价格达到严格跌停状态")), "全市场统计");
    case "risk-stocks": return exact(riskStocks.map((item) => stock(item, "跌停、炸板或当前跌幅不高于 -3%")));
    case "active-stocks": return exact(model.stocks.map((item) => stock(item, "当前接口返回的代表股票样本")));
    case "top-stock": {
      const item = [...model.stocks].filter((candidate) => known(candidate.change)).sort((left, right) => compareDesc(left.change, right.change))[0];
      return item ? exact([stock(item, "当前代表样本中涨幅领先")]) : aggregate("行情样本缺少可验证涨跌幅，无法形成逐股明细。");
    }
    case "high-amplitude": {
      const item = [...model.stocks].filter((candidate) => known(candidate.amplitude)).sort((left, right) => compareDesc(left.amplitude, right.amplitude))[0];
      return item ? exact([stock(item, `振幅 ${item.amplitude!.toFixed(2)}%`)]) : aggregate("行情样本缺少高低价，无法形成逐股明细。");
    }
    case "attention-top": {
      const item = [...model.stocks].filter((candidate) => known(candidate.attentionScore)).sort((left, right) => compareDesc(left.attentionScore, right.attentionScore))[0];
      return item ? exact([stock(item, `观察热度分 ${item.attentionScore!.toFixed(0)}`)]) : aggregate("行情、成交额和关联证据不足，无法形成逐股明细。");
    }
    case "theme-stock-top": {
      const item = [...model.stocks].filter((candidate) => candidate.themes.length > 0).sort((left, right) => right.themes.length - left.themes.length)[0];
      return item ? exact([stock(item, `已关联题材：${item.themes.join(" / ")}`)]) : aggregate("没有股票同时具备可追溯题材证据。");
    }
    case "history-new-high": return data.review ? exact((data.review.new_high_100 ?? []).map((item) => reviewStock(item, "收盘创 100 日新高"))) : aggregate("本地日线复盘尚未完成。");
    case "history-previous-limit": return data.review ? exact((data.review.previous_limit_up ?? []).map((item) => reviewStock(item, "上一交易日严格涨停"))) : aggregate("本地日线复盘尚未完成。");
    case "consecutive-count": return data.review ? exact((data.review.consecutive_limit_up ?? []).map((item) => reviewStock(item, `连续 ${item.board_count ?? "--"} 个交易日收盘涨停`))) : aggregate("本地日线复盘尚未完成。");
    case "top-board": {
      const rows = data.review?.consecutive_limit_up ?? [];
      const maxBoard = Math.max(...rows.map((item) => item.board_count ?? 0), 0);
      return maxBoard > 0 ? exact(rows.filter((item) => item.board_count === maxBoard).map((item) => reviewStock(item, `当前最高连板 ${maxBoard} 板`))) : aggregate("本地连续日线没有可用连板高度。");
    }
    case "first-board": return data.review ? exact((data.review.first_limit_up ?? []).map((item) => reviewStock(item, "当日涨停且上一交易日未涨停"))) : aggregate("本地日线复盘尚未完成。");
    case "volume-breakout": return data.review ? exact((data.review.volume_breakouts ?? []).map((item) => reviewStock(item, "60 日收盘新高且量能达到规则"))) : aggregate("本地日线复盘尚未完成。");
    case "previous-high": return data.review ? exact((data.review.previous_high_breakouts ?? []).map((item) => reviewStock(item, "突破前 20 日高点并放量"))) : aggregate("本地日线复盘尚未完成。");
    case "low-volume": return data.review ? exact((data.review.low_position_volume ?? []).map((item) => reviewStock(item, "120 日区间下部且出现放量"))) : aggregate("本地日线复盘尚未完成。");
    case "seat-stocks": return data.review ? exact((data.review.dragon_tiger ?? []).map((item) => listedStock(item, `龙虎榜原因：${item.reason}`))) : aggregate("龙虎榜接口和本地缓存均不可用。");
    case "seat-count": return data.review ? exact((data.review.dragon_tiger ?? []).map((item) => listedStock(item, `包含 ${item.seats.length} 条可验证席位明细`)), "席位明细统计") : aggregate("龙虎榜席位尚未取得。");
    case "large-order":
    case "large-order-net": return data.large_order_flows?.length ? exact(data.large_order_flows.map((item) => ({ symbol: item.symbol, name: item.name?.trim() || "名称待补齐", reason: "真实大单与超大单净额样本", value: signedMoney(Number(item.main_net_yi)) }))) : aggregate("当前响应没有真实个股资金流样本。");
    case "rising": return aggregate("当前接口仅返回全市场聚合值，暂无成员级明细；不会用代表股票样本冒充全部上涨股票。");
    case "falling": return aggregate("当前接口仅返回全市场聚合值，暂无成员级明细；不会用代表股票样本冒充全部下跌股票。");
    case "market-amount": return aggregate("两市成交是全市场聚合金额，不存在可逐股等价展开的成员名单。");
    case "sector-total": case "sector-positive": case "sector-limit": case "top-sector": case "top-sector-breadth": case "top-sector-amount":
      return aggregate("该指标统计对象是板块，不是股票；当前股票钻取面板不会把板块数量伪装成个股名单。");
    default: return aggregate(insight.quality === "unavailable" ? insight.detail : "该指标当前只有聚合值或综合评分，没有严格同口径的逐股成员明细。");
  }
}
