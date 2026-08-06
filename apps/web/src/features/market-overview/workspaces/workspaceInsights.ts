import type { MarketOverviewResponse } from "../types";
import { hasDragonTigerEvidence } from "./workspaceEvidence";
import type { WorkspaceMarketModel } from "./workspaceSelectors";

export type InsightQuality = "ready" | "partial" | "unavailable";
export type InsightTone = "positive" | "warning" | "danger" | "neutral";

export type WorkspaceInsight = {
  key: MetricKey;
  label: string;
  value: string;
  detail: string;
  quality: InsightQuality;
  tone: InsightTone;
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

const ready = (key: MetricKey, label: string, value: string, detail: string, tone: InsightTone, icon: WorkspaceInsight["icon"]): WorkspaceInsight => ({ key, label, value, detail, quality: "ready", tone, icon });
const unavailable = (key: MetricKey, label: string, detail: string, icon: WorkspaceInsight["icon"]): WorkspaceInsight => ({ key, label, value: "未接入", detail, quality: "unavailable", tone: "warning", icon });
const countSymbols = (items: Array<{ symbols: string[] }>) => new Set(items.flatMap((item) => item.symbols)).size;
const signedMoney = (value: number) => `${value >= 0 ? "+" : ""}${value.toFixed(2)}亿`;

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
  const seatEvidenceReady = hasDragonTigerEvidence(review);
  const seats = review?.dragon_tiger.flatMap((item) => item.seats) ?? [];
  const seatNet = seats.reduce((sum, item) => sum + Number(item.net_amount_yi || 0), 0);
  const topSeat = [...seats].sort((a, b) => Math.abs(Number(b.net_amount_yi)) - Math.abs(Number(a.net_amount_yi)))[0];
  const topSector = model.sectors[0];
  const topStock = [...model.stocks].sort((a, b) => b.change - a.change)[0];
  const topAttention = [...model.stocks].sort((a, b) => b.attentionScore - a.attentionScore)[0];
  const topThemeStock = [...model.stocks].sort((a, b) => b.themes.length - a.themes.length)[0];
  const topAmplitude = [...model.stocks].sort((a, b) => b.amplitude - a.amplitude)[0];
  const gapsUp = model.stocks.filter((item) => item.gap >= 2);
  const gapsDown = model.stocks.filter((item) => item.gap <= -2);
  const auctionPass = model.stocks.filter((item) => item.gap >= -1 && item.gap <= 4 && item.change >= item.gap - 1 && item.closePosition >= 50 && item.amount > 0);
  const riskStocks = model.stocks.filter((item) => item.state === "broken_limit_up" || item.state === "limit_down" || item.change <= -3);
  const coverage = review && review.universe_count > 0 ? review.history_ready_count / review.universe_count * 100 : 0;

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
    case "gap-up": return ready(key, "高开 >= 2%", String(gapsUp.length), "开盘价相对昨收", "positive", "auction");
    case "gap-down": return ready(key, "低开 <= -2%", String(gapsDown.length), "开盘价相对昨收", "danger", "auction");
    case "gap-recovery": return ready(key, "高开延续", String(gapsUp.filter((item) => item.change >= item.gap - 1).length), "现涨幅未明显弱于缺口", "positive", "auction");
    case "auction-pass": return ready(key, "竞价规则通过", String(auctionPass.length), "缺口、现价、收盘位置、成交均通过", "positive", "auction");
    case "order-book": return unavailable(key, "委托/封单证据", "当前响应没有逐笔委托队列", "data");
    case "limit-up": return ready(key, "严格涨停", String(data.limit_ecology.limit_up_count), "按现价与涨停价判定", "positive", "limit");
    case "broken-limit": return ready(key, "触板未封", String(data.limit_ecology.broken_limit_up_count), "最高触板但现价未封", "warning", "risk");
    case "limit-down": return ready(key, "当前跌停", String(data.limit_ecology.limit_down_count), "严格现价风险状态", "danger", "risk");
    case "seal-rate": return ready(key, "封板率", data.limit_ecology.seal_rate_percent ? `${data.limit_ecology.seal_rate_percent}%` : "--", "封板 / 全部触板", "positive", "limit");
    case "risk-stocks": return ready(key, "风险股票", String(riskStocks.length), "跌停、炸板或跌幅 <= -3%", "danger", "risk");
    case "sector-total": return ready(key, "板块样本", String(model.sectors.length), "本地板块快照", "neutral", "sector");
    case "sector-positive": return ready(key, "上涨板块", String(model.sectors.filter((item) => item.change > 0).length), "板块涨跌幅 > 0", "positive", "sector");
    case "sector-limit": return ready(key, "涨停扩散板块", String(model.sectors.filter((item) => item.limit_up_count > 0).length), "板块内至少 1 只涨停", "positive", "sector");
    case "top-sector": return ready(key, "综合强度第一", topSector?.name ?? "--", topSector ? `强度 ${topSector.strengthScore.toFixed(0)} / 100` : "板块快照不可用", "positive", "sector");
    case "top-sector-breadth": return ready(key, "领涨板块广度", topSector ? `${topSector.breadthPercent.toFixed(0)}%` : "--", topSector?.name ?? "板块快照不可用", "positive", "sector");
    case "top-sector-amount": return ready(key, "板块成交活跃", topSector ? `${topSector.amount.toFixed(0)}亿` : "--", "仅表示成交额，不代表净流入", "neutral", "sector");
    case "sentiment": return ready(key, "市场情绪", data.sentiment.score ?? "--", data.sentiment.band, "neutral", "pulse");
    case "rising": return ready(key, "上涨家数", String(data.breadth.rising_count), `${data.breadth.valid_count} 只有效行情`, "positive", "pulse");
    case "falling": return ready(key, "下跌家数", String(data.breadth.falling_count), `${data.breadth.valid_count} 只有效行情`, "danger", "pulse");
    case "market-amount": return ready(key, "两市成交", data.liquidity.total_amount_yi ? `${data.liquidity.total_amount_yi}亿` : "--", data.liquidity.relative_amount ? `基准 ${data.liquidity.relative_amount}x` : "历史基准不足", "neutral", "pulse");
    case "regime": return ready(key, "市场风格", data.regime?.regime ?? "待确认", data.regime ? `仓位系数 ${data.regime.market_coef}` : "因子覆盖不足", "neutral", "pulse");
    case "risk-score": return ready(key, "市场风险分", data.regime?.risk_score ?? "--", data.regime?.quality === "ready" ? "风格模型已核验" : "等待因子", "danger", "risk");
    case "heat-score": return ready(key, "市场热度分", data.regime?.heat_score ?? "--", data.regime?.quality === "ready" ? "风格模型已核验" : "等待因子", "positive", "pulse");
    case "active-stocks": return ready(key, "行情样本", String(model.stocks.length), "接口返回的代表股票", "neutral", "stock");
    case "top-stock": return ready(key, "涨幅领先", topStock?.name ?? "--", topStock ? `${topStock.symbol} ${topStock.change >= 0 ? "+" : ""}${topStock.change.toFixed(2)}%` : "行情样本为空", "positive", "stock");
    case "high-amplitude": return ready(key, "最大振幅", topAmplitude ? `${topAmplitude.amplitude.toFixed(2)}%` : "--", topAmplitude ? `${topAmplitude.name} ${topAmplitude.symbol}` : "行情样本为空", "warning", "stock");
    case "attention-top": return ready(key, "观察热度第一", topAttention?.name ?? "--", topAttention ? `量价资讯合成分 ${topAttention.attentionScore.toFixed(0)}` : "行情样本为空", "positive", "stock");
    case "theme-stock-top": return ready(key, "题材叠加最多", topThemeStock?.name ?? "--", topThemeStock ? `${topThemeStock.themes.length} 个已关联题材` : "行情样本为空", "warning", "theme");
    case "history-coverage": return review && review.universe_count > 0 && review.history_ready_count > 0
      ? ready(key, "日线覆盖", `${coverage.toFixed(1)}%`, `${review.history_ready_count}/${review.universe_count}`, coverage >= 80 ? "positive" : "warning", "history")
      : unavailable(key, "日线覆盖", "本地日线没有可用历史样本", "history");
    case "history-new-high": return unavailable(key, "百日新高清单", "当前响应未返回百日新高逐股结果", "history");
    case "history-previous-limit": return unavailable(key, "昨涨停反馈", "当前响应未返回上一交易日涨停名单", "history");
    case "interval-result": return unavailable(key, "区间统计结果", "尚未选择并计算明确起止区间", "history");
    case "consecutive-count": return review ? ready(key, "连续涨停", String(review.consecutive_limit_up.length), "至少 2 个交易日连续收盘涨停", "positive", "history") : unavailable(key, "连续涨停", "本地日线复盘尚未完成", "history");
    case "top-board": return review ? ready(key, "最高连板", `${Math.max(0, ...review.consecutive_limit_up.map((item) => item.board_count ?? 0))}板`, "来自本地连续日线", "positive", "history") : unavailable(key, "最高连板", "本地日线复盘尚未完成", "history");
    case "first-board": return review ? ready(key, "首板股票", String(review.first_limit_up.length), "当日涨停且上一日未涨停", "positive", "history") : unavailable(key, "首板股票", "本地日线复盘尚未完成", "history");
    case "volume-breakout": return review ? ready(key, "放量突破", String(review.volume_breakouts.length), "60 日收盘新高且量能 >= 1.8x", "positive", "history") : unavailable(key, "放量突破", "本地日线复盘尚未完成", "history");
    case "previous-high": return review ? ready(key, "突破前高", String(review.previous_high_breakouts.length), "突破前 20 日高点并放量", "positive", "history") : unavailable(key, "突破前高", "本地日线复盘尚未完成", "history");
    case "low-volume": return review ? ready(key, "低位放量", String(review.low_position_volume.length), "120 日区间下部且放量", "warning", "history") : unavailable(key, "低位放量", "本地日线复盘尚未完成", "history");
    case "seat-stocks": return seatEvidenceReady ? ready(key, "上榜股票", String(review!.dragon_tiger.length), "东方财富公开龙虎榜", "neutral", "seat") : unavailable(key, "上榜股票", "龙虎榜接口和本地缓存均不可用", "seat");
    case "seat-count": return seatEvidenceReady ? ready(key, "可验证席位", String(seats.length), "含席位名称及买卖金额", "neutral", "seat") : unavailable(key, "可验证席位", "龙虎榜席位尚未取得", "seat");
    case "seat-net": return seatEvidenceReady ? ready(key, "席位净买额", signedMoney(seatNet), "按公开席位净额合计", seatNet >= 0 ? "positive" : "danger", "seat") : unavailable(key, "席位净买额", "龙虎榜席位尚未取得", "seat");
    case "top-seat": return seatEvidenceReady ? ready(key, "净额最大席位", topSeat?.seat_name ?? "--", topSeat ? signedMoney(Number(topSeat.net_amount_yi)) : "当日无席位明细", "neutral", "seat") : unavailable(key, "净额最大席位", "龙虎榜席位尚未取得", "seat");
    case "large-order": return unavailable(key, "逐笔大单方向", "当前响应没有逐笔方向和真实净流入", "data");
    case "large-order-buy": return unavailable(key, "大单买入额", "缺少逐笔方向，不能从总成交额推算", "data");
    case "large-order-sell": return unavailable(key, "大单卖出额", "缺少逐笔方向，不能从总成交额推算", "data");
    case "large-order-net": return unavailable(key, "大单净流入", "买卖方向字段未接入，保持不可用", "data");
    case "sector-flow": return unavailable(key, "板块净流入", "当前响应没有板块资金净流入序列", "data");
    case "sector-flow-timeline": return unavailable(key, "资金时间序列", "未取得逐时板块净流入记录", "data");
    case "sector-flow-direction": return unavailable(key, "主买方向", "板块成交额不能判断买卖方向", "data");
    case "sector-flow-persistence": return unavailable(key, "资金持续性", "没有连续净流入序列，不能测算持续性", "data");
    case "iwencai": return unavailable(key, "问财语义结果", "当前执行的是本地规则，不冒充问财官方结果", "data");
    case "review-date": return ready(key, "复盘交易日", review?.latest_trade_date ?? "--", review ? "本地日线复盘日期" : "复盘尚未完成", "neutral", "history");
    case "review-quality": return ready(key, "复盘质量", review?.quality === "ready" ? "完整" : review?.quality === "partial" ? "部分" : "待准备", review?.source ?? "暂无复盘来源", review?.quality === "ready" ? "positive" : "warning", "data");
  }
}

export function buildWorkspaceInsights(feature: string, data: MarketOverviewResponse, model: WorkspaceMarketModel): WorkspaceInsight[] {
  const profile = WORKSPACE_INSIGHT_PROFILES[feature];
  if (!profile) throw new Error(`信息总览缺少关键指标定义：${feature}`);
  return profile.map((key) => metric(key, data, model));
}
