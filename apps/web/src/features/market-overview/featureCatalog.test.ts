import { describe, expect, it } from "vitest";

import { featureRows } from "./featureCatalog";

describe("market overview feature catalog", () => {
  it("keeps all 50 menu labels unique and orders related workflows together", () => {
    const labels = featureRows.flat();
    expect(labels).toHaveLength(50);
    expect(new Set(labels)).toHaveLength(50);
    expect(featureRows.map((row) => row.length)).toEqual([19, 19, 12]);
    expect(labels).toEqual([
      "盘中异动", "异动语音播报",
      "隔夜单/抢筹", "竞价封单", "竞价异动", "竞价选股", "开盘啦",
      "情绪周期", "涨停板", "昨涨停", "跌停板", "炸板", "首板梯队", "连板梯队", "连板表现", "龙头梯队", "龙头晋级", "涨停复盘啦",
      "AI+题材", "板块精选", "板块赛道", "板块涨停", "强度风口", "题材库", "题材挖掘", "热点播报", "热点解读", "概念叠加", "非研产业库",
      "人气榜", "七大人气榜", "游资追踪", "游资动向", "龙虎榜", "主力大单监控", "板块资金动图", "个股异动", "异动提醒",
      "百日新高", "百日新高趋势", "放量突破", "突破前高", "低位放量", "区间统计",
      "AI+选股", "问财选股", "个股详情", "投资日历", "复盘统计大全", "异动统计大全",
    ]);
  });
});
