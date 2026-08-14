import { describe, expect, it } from "vitest";

import { featureCatalog, featureRows, featureMeta } from "./featureCatalog";

describe("market overview feature catalog", () => {
  it("keeps all 50 menu labels unique and orders related workflows together", () => {
    const labels = featureRows.flat();
    expect(labels).toHaveLength(50);
    expect(new Set(labels)).toHaveLength(50);
    expect(featureRows.map((row) => row.length)).toEqual([19, 19, 12]);
    expect(labels).toEqual([
      "盘中异动", "异动语音播报",
      "板块资金动图", "竞价封单", "竞价异动", "竞价选股", "开盘啦",
      "情绪周期", "涨停板", "昨涨停", "跌停板", "炸板", "首板梯队", "连板梯队", "连板表现", "龙头梯队", "龙头晋级", "涨停复盘啦",
      "AI+题材", "板块精选", "板块赛道", "板块涨停", "强度风口", "题材库", "题材挖掘", "热点播报", "热点解读", "概念叠加", "非研产业库",
      "人气榜", "七大人气榜", "游资追踪", "游资动向", "龙虎榜", "主力大单监控", "隔夜单/抢筹", "个股异动", "异动提醒",
      "百日新高", "百日新高趋势", "放量突破", "突破前高", "低位放量", "区间统计",
      "AI+选股", "问财选股", "个股详情", "投资日历", "复盘统计大全", "异动统计大全",
    ]);
  });

  it("keeps the established flat display labels and capability notes", () => {
    expect(featureMeta["开盘啦"]).toMatchObject({ key: "开盘啦", label: "开盘啦", family: "竞价与盘中" });
    expect(featureMeta["涨停复盘啦"].label).toBe("涨停复盘啦");
    expect(featureMeta["人气榜"].label).toBe("人气榜");
    expect(featureMeta["七大人气榜"].label).toBe("七大人气榜");
    expect(featureMeta["问财选股"].label).toBe("问财选股");
    expect(featureMeta["非研产业库"].label).toBe("非研产业库");
    expect(featureMeta["个股详情"].label).toBe("个股详情");
    expect(featureMeta["隔夜单/抢筹"]).toMatchObject({ label: "隔夜单/抢筹", family: "竞价与盘中" });
    expect(featureMeta["板块资金动图"]).toMatchObject({ label: "板块资金动图", family: "题材、板块与资金" });
    expect(featureMeta["隔夜单/抢筹"].note).toMatch(/委托|缺少/);
    expect(featureCatalog).toHaveLength(50);
    expect(new Set(featureCatalog.map((item) => item.key))).toHaveLength(50);
  });
});
