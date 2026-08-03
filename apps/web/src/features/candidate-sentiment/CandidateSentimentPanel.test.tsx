import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CandidateSentimentPanel } from "./CandidateSentimentPanel";
import type { CandidateSentimentSnapshot } from "./types";


function panelSentiment(
  overrides: Partial<CandidateSentimentSnapshot> = {},
): CandidateSentimentSnapshot {
  return {
    snapshot_id: "candidate-sentiment-600000",
    candidate_snapshot_id: "candidate-1",
    candidate_input_hash: "a".repeat(64),
    symbol: "600000",
    quality: "ready",
    freshness: "current",
    score: "82",
    band: "overheated",
    coverage_percent: "100",
    components: [
      { name: "news", status: "ready", score: "75", weight: "40", summary: "已核验新闻整体偏正面", observed_at: "2026-07-18T14:00:00+08:00", evidence_ids: ["news-event-1", "interpretation-1"] },
      { name: "hotspot", status: "ready", score: "90", weight: "30", summary: "题材热点正在延续", observed_at: "2026-07-18T14:01:00+08:00", evidence_ids: ["hotspot-event-1"] },
      { name: "fund_flow", status: "ready", score: "80", weight: "30", summary: "近 5 日主力资金偏流入", observed_at: "2026-07-18T14:02:00+08:00", evidence_ids: ["fund-flow-1234567890abcdef12345678"] },
    ],
    primary_reason: "热点延续并有资金配合。",
    primary_risk: "题材热度较高，追涨和拥挤风险上升。",
    beginner_guidance: "关注拥挤和回落风险，不把高热度当成安全。",
    observed_at: "2026-07-18T14:02:00+08:00",
    generated_at: "2026-07-18T14:02:05+08:00",
    source_snapshot_ids: [
      "news-event-1",
      "interpretation-1",
      "hotspot-event-1",
      "fund-flow-1234567890abcdef12345678",
    ],
    formula_version: "candidate-sentiment-v1",
    ...overrides,
  };
}


describe("CandidateSentimentPanel", () => {
  it("shows total score, three components, evidence and beginner guidance", () => {
    render(<CandidateSentimentPanel sentiment={panelSentiment()} />);

    const panel = screen.getByRole("region", { name: "个股情绪观察" });
    expect(panel).toHaveTextContent("82");
    expect(panel).toHaveTextContent("情绪过热");
    expect(panel).toHaveTextContent("覆盖率 100%");
    expect(panel).toHaveTextContent("新闻倾向");
    expect(panel).toHaveTextContent("题材热度");
    expect(panel).toHaveTextContent("资金方向");
    expect(panel).toHaveTextContent("已核验新闻整体偏正面");
    expect(panel).toHaveTextContent("news-event-1");
    expect(panel).toHaveTextContent("fund-flow-1234567890abcdef12345678");
    expect(panel).toHaveTextContent("热点延续并有资金配合");
    expect(panel).toHaveTextContent("追涨和拥挤风险");
    expect(panel).toHaveTextContent("关注拥挤和回落风险");
    expect(panel).toHaveTextContent("数据时间");
    expect(panel).toHaveTextContent("独立观察指标 · 不改变候选排序与行动结论");
  });

  it("shows unavailable components without inventing scores", () => {
    const unavailable = panelSentiment({
      quality: "unavailable",
      score: null,
      band: "unavailable",
      coverage_percent: "40",
      components: panelSentiment().components.map((component) => ({
        ...component,
        status: "unavailable" as const,
        score: null,
        observed_at: null,
        evidence_ids: [],
        summary: `${component.name} 数据不可用`,
      })),
      source_snapshot_ids: [],
    });
    render(<CandidateSentimentPanel sentiment={unavailable} />);

    const panel = screen.getByRole("region", { name: "个股情绪观察" });
    expect(panel).toHaveTextContent("暂不可评分");
    expect(panel).toHaveTextContent("覆盖率 40%");
    expect(within(panel).getAllByText("暂不可用")).toHaveLength(3);
    expect(panel).not.toHaveTextContent("0 分");
  });
});
