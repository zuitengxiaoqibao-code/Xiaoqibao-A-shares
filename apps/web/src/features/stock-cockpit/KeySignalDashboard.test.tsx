import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CandidateSentimentSnapshot } from "../candidate-sentiment/types";
import { KeySignalDashboard } from "./KeySignalDashboard";
import type { StockAssessment } from "./types";

const observedAt = "2026-07-20T10:30:00+08:00";

function assessment(overrides: Partial<StockAssessment> = {}): StockAssessment {
  return {
    assessment_id: "assessment-1",
    symbol: "603629",
    action: "observe",
    conclusion: "量价与新闻证据相互印证，继续观察。",
    confidence: "0.85",
    supporting_evidence: [],
    contrary_evidence: [],
    risks: ["资金流仍需继续确认。"],
    invalidation_conditions: ["趋势转弱"],
    generated_at: observedAt,
    ...overrides,
  };
}

function sentiment(overrides: Partial<CandidateSentimentSnapshot> = {}): CandidateSentimentSnapshot {
  return {
    snapshot_id: "sentiment-1",
    candidate_snapshot_id: "candidate-1",
    candidate_input_hash: "hash-1",
    symbol: "603629",
    quality: "ready",
    freshness: "current",
    score: "70.71",
    band: "positive",
    coverage_percent: "100",
    components: [],
    primary_reason: "新闻与题材热度偏积极。",
    primary_risk: "追涨风险上升。",
    beginner_guidance: "等待价格确认。",
    observed_at: observedAt,
    generated_at: observedAt,
    source_snapshot_ids: ["source-1"],
    formula_version: "candidate-sentiment-v1",
    ...overrides,
  };
}

describe("KeySignalDashboard", () => {
  it("shows action, confidence, evidence coverage and verified sentiment without inventing a risk score", () => {
    render(
      <KeySignalDashboard
        assessment={assessment()}
        overallQuality="ready"
        readySources={6}
        totalSources={6}
        candidateSentiment={sentiment()}
      />,
    );

    const dashboard = screen.getByRole("region", { name: "关键状态仪表" });
    expect(dashboard).toHaveClass("action-observe");
    expect(dashboard).toHaveTextContent("加入观察");
    expect(dashboard).toHaveTextContent("量价与新闻证据相互印证，继续观察。");
    expect(screen.getByRole("meter", { name: "决策置信度" })).toHaveAttribute("aria-valuenow", "85");
    expect(screen.getByRole("meter", { name: "证据覆盖率" })).toHaveAttribute("aria-valuenow", "100");
    expect(screen.getByRole("meter", { name: "个股情绪" })).toHaveAttribute("aria-valuenow", "70.71");
    expect(screen.getAllByRole("meter")).toHaveLength(3);
    expect(within(dashboard).getByText("资金流仍需继续确认。")).toBeInTheDocument();
    expect(dashboard).not.toHaveTextContent("风险分");
    expect(dashboard).not.toHaveTextContent("情绪不能覆盖当前风险结论");
  });

  it("makes an avoid action primary and warns when positive sentiment conflicts with the risk conclusion", () => {
    render(
      <KeySignalDashboard
        assessment={assessment({ action: "avoid", conclusion: "风险分区阻断，当前应回避。" })}
        overallQuality="ready"
        readySources={6}
        totalSources={6}
        candidateSentiment={sentiment()}
      />,
    );

    const dashboard = screen.getByRole("region", { name: "关键状态仪表" });
    expect(dashboard).toHaveClass("action-avoid");
    expect(dashboard).toHaveTextContent("回避");
    expect(dashboard).toHaveTextContent("情绪不能覆盖当前风险结论");
    expect(screen.getByLabelText("关键风险提醒")).toHaveClass("tone-danger");
  });

  it("degrades partial evidence and missing sentiment without fabricating a meter value", () => {
    render(
      <KeySignalDashboard
        assessment={assessment({ action: "wait", confidence: "0.52" })}
        overallQuality="partial"
        readySources={1}
        totalSources={4}
        candidateSentiment={null}
      />,
    );

    const dashboard = screen.getByRole("region", { name: "关键状态仪表" });
    expect(dashboard).toHaveClass("action-wait", "evidence-warning");
    expect(screen.getByRole("meter", { name: "证据覆盖率" })).toHaveAttribute("aria-valuenow", "25");
    expect(screen.queryByRole("meter", { name: "个股情绪" })).not.toBeInTheDocument();
    expect(dashboard).toHaveTextContent("未评分");
    expect(dashboard).toHaveTextContent("1 / 4 类可用");
  });
});
