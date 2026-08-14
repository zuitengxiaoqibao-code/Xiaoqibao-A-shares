import { describe, expect, it } from "vitest";

import { presentLatestTip } from "./latestTipPresentation";
import type { LatestTipItem } from "./types";


function tip(overrides: Partial<LatestTipItem> = {}): LatestTipItem {
  return {
    id: "tip-1",
    category: "业绩预告",
    title: "季度经营数据同比增长",
    date: "2026-03-31",
    tone: "positive",
    summary: "营业收入 58571.50 万元，同比增长 8.04%；净利润 2717.81 万元，同比增长 17.86%",
    source: "mootdx-f10",
    observed_at: "2026-08-12T10:00:00+08:00",
    raw_text: "||| 通达信沪深京F10 | 营业收入 58571.50 万元 | 净利润 2717.81 万元 |||",
    ...overrides,
  };
}

describe("presentLatestTip", () => {
  it("turns positive financial facts into readable fact, impact and watch items", () => {
    const presentation = presentLatestTip(tip());

    expect(presentation.fact).toContain("营业收入 58571.50 万元，同比增长 8.04%");
    expect(presentation.impact).toContain("收入与利润同比改善");
    expect(presentation.watch).toContain("经营现金流");
    expect(presentation.rawEvidence).not.toContain("|||");
    expect(presentation.rawEvidence).not.toContain("通达信沪深京F10");
  });

  it("keeps an unlock as a risk observation instead of inventing an outcome", () => {
    const presentation = presentLatestTip(tip({
      category: "风险提醒",
      title: "高比例限售股解禁",
      tone: "risk",
      summary: "首发限售 · 10000.0万股 · 占比 6.50%",
      raw_text: "解禁日期 2026-09-01；解禁比例 6.50%",
    }));

    expect(presentation.impact).toContain("潜在供给压力");
    expect(presentation.watch).toContain("实际减持");
  });
});
