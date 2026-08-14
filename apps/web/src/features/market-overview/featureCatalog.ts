export const featureRows = [
  ["盘中异动", "异动语音播报", "板块资金动图", "竞价封单", "竞价异动", "竞价选股", "开盘啦", "情绪周期", "涨停板", "昨涨停", "跌停板", "炸板", "首板梯队", "连板梯队", "连板表现", "龙头梯队", "龙头晋级", "涨停复盘啦", "AI+题材"],
  ["板块精选", "板块赛道", "板块涨停", "强度风口", "题材库", "题材挖掘", "热点播报", "热点解读", "概念叠加", "非研产业库", "人气榜", "七大人气榜", "游资追踪", "游资动向", "龙虎榜", "主力大单监控", "隔夜单/抢筹", "个股异动", "异动提醒"],
  ["百日新高", "百日新高趋势", "放量突破", "突破前高", "低位放量", "区间统计", "AI+选股", "问财选股", "个股详情", "投资日历", "复盘统计大全", "异动统计大全"],
] as const;

export type MarketFeatureLabel = (typeof featureRows)[number][number];

export type MarketFeature = {
  key: MarketFeatureLabel;
  label: string;
  family: string;
  note?: string;
};

const capabilityNotes: Partial<Record<MarketFeatureLabel, string>> = {
  "隔夜单/抢筹": "当前只验证高开缺口，缺少真实委托队列",
  "竞价封单": "封板价格可验证，封单金额需要真实委托队列",
};

const rowFamilies = ["竞价与盘中", "题材、板块与资金", "量价筛选与复盘"] as const;

const featureFamilies: Partial<Record<MarketFeatureLabel, string>> = {
  "隔夜单/抢筹": "竞价与盘中",
  "板块资金动图": "题材、板块与资金",
};

export const featureCatalog: MarketFeature[] = featureRows.flatMap((row, rowIndex) => row.map((key) => ({
  key,
  // Keep the user's established flat menu vocabulary stable; family is metadata only.
  label: key,
  family: featureFamilies[key] ?? rowFamilies[rowIndex],
  ...(capabilityNotes[key] ? { note: capabilityNotes[key] } : {}),
})));

export const featureMeta = Object.fromEntries(
  featureCatalog.map((item) => [item.key, item]),
) as Record<MarketFeatureLabel, MarketFeature>;

export function featureDisplayLabel(key: string): string {
  return featureMeta[key as MarketFeatureLabel]?.label ?? key;
}
